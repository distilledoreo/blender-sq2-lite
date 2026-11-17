#!/usr/bin/env python3
"""Copy the DLLs the arm64 Blender build needs but 3.6 does not install.

3.6's install rules name dependencies the way the 3.6-era 3.x dependency set
did (``libfftw3-3.dll``, ``opencolorio_2_2.dll``, ...), so against the 4.2
arm64 set several imported DLLs are never installed and ``blender.exe`` dies
with 0xC0000135. Walk the PE import graph from ``blender.exe`` and copy
anything unresolved out of the dependency tree into the staged bin directory.

Usage: stage_runtime.py --tree <build/bin> --lib <lib/windows_arm64>
"""

import argparse
import os
import shutil
import struct
import sys

# Windows resolves these API sets itself; no file exists for them.
APISET_PREFIXES = ("api-ms-win-", "ext-ms-")


def pe_imports(path):
    """Return the DLL names imported by the PE image at ``path``."""
    with open(path, "rb") as handle:
        data = handle.read()

    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE image: %s" % path)
    nsections = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic not in (0x10B, 0x20B):
        raise ValueError("unknown PE optional header in %s" % path)
    data_dirs = opt + (112 if magic == 0x20B else 96)
    import_rva = struct.unpack_from("<I", data, data_dirs + 8)[0]
    if not import_rva:
        return []

    sections = []
    table = opt + opt_size
    for i in range(nsections):
        offset = table + 40 * i
        vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, offset + 8)
        sections.append((vaddr, vsize, rawptr, rawsize))

    def rva_to_offset(rva):
        for vaddr, vsize, rawptr, rawsize in sections:
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                return rawptr + (rva - vaddr)
        raise ValueError("RVA 0x%X outside every section of %s" % (rva, path))

    names = []
    offset = rva_to_offset(import_rva)
    while True:
        entry = data[offset:offset + 20]
        if len(entry) < 20 or entry == b"\0" * 20:
            break
        name_rva = struct.unpack_from("<I", entry, 12)[0]
        if not name_rva:
            break
        start = rva_to_offset(name_rva)
        names.append(data[start:data.index(b"\0", start)].decode())
        offset += 20
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", required=True, help="staged bin directory")
    parser.add_argument("--lib", required=True, help="dependency tree root")
    args = parser.parse_args(argv)

    exe = os.path.join(args.tree, "blender.exe")
    if not os.path.isfile(exe):
        print("blender.exe not found in %s" % args.tree, file=sys.stderr)
        return 2

    # First match wins, so the top-level packages shadow duplicates.
    index = {}
    for root, _dirs, files in os.walk(args.lib):
        for name in files:
            index.setdefault(name.lower(), os.path.join(root, name))

    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    search = [
        args.tree,
        os.path.join(args.tree, "blender.shared"),
        os.path.join(system_root, "System32"),
        os.path.join(system_root, "SysWOW64"),
    ]

    def locate(name):
        for directory in search:
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate):
                return candidate
        return None

    resolved = {}
    missing = {}
    copied = []
    scanned = set()
    queue = [exe]
    while queue:
        module = queue.pop()
        if module.lower() in scanned:
            continue
        scanned.add(module.lower())
        try:
            deps = pe_imports(module)
        except (ValueError, struct.error) as exc:
            print("scan error: %s" % exc, file=sys.stderr)
            continue
        for dep in deps:
            key = dep.lower()
            if key in resolved:
                continue
            if key.startswith(APISET_PREFIXES):
                resolved[key] = None
                continue
            found = locate(dep)
            if found:
                resolved[key] = found
                # System DLLs are leaves we cannot stage, everything else has to
                # be walked so its own imports are checked too.
                if not found.lower().startswith(system_root.lower()):
                    queue.append(found)
                continue
            source = index.get(key)
            if source is None:
                missing[dep] = os.path.basename(module)
                continue
            target = os.path.join(args.tree, dep)
            shutil.copy2(source, target)
            copied.append((dep, source))
            resolved[key] = target
            queue.append(target)

    for dep, source in copied:
        print("staged %-34s from %s" % (dep, source))
    print("resolved %d modules, staged %d DLLs" % (len(resolved), len(copied)))
    if missing:
        print("MISSING:")
        for dep, importer in sorted(missing.items()):
            print("  %-34s needed by %s" % (dep, importer))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
