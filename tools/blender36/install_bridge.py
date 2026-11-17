"""Install the SQ2 legacy bridge into a Blender 3.6 install.

Copies tools/blender36/bridge/sq2_legacy_bridge.py to
<install>/<version>/scripts/startup/ so it loads at boot (no add-on to enable).

Usage:
  python tools/blender36/install_bridge.py <blender-install-root>

<blender-install-root> is the folder containing blender.exe, e.g.
blender-3.6.23-windows-x64.
"""
import glob
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "bridge", "sq2_legacy_bridge.py")


def find_version_dir(root):
    """Blender 2.8+ keeps its data in <root>/<major.minor>/."""
    candidates = [
        d for d in glob.glob(os.path.join(root, "*"))
        if os.path.isdir(d) and os.path.isdir(os.path.join(d, "scripts"))
    ]
    if not candidates:
        raise SystemExit("no version dir with scripts/ under %s" % root)
    return candidates[0]


def main(argv):
    if len(argv) != 2:
        raise SystemExit(__doc__)
    root = os.path.abspath(argv[1])
    if not os.path.exists(os.path.join(root, "blender.exe")):
        raise SystemExit("no blender.exe in %s" % root)
    version_dir = find_version_dir(root)
    startup = os.path.join(version_dir, "scripts", "startup")
    os.makedirs(startup, exist_ok=True)
    dst = os.path.join(startup, os.path.basename(SRC))
    shutil.copyfile(SRC, dst)
    print("installed %s -> %s" % (SRC, dst))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
