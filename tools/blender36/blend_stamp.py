"""Read or rewrite the version stamp in a .blend header.

A .blend starts with "BLENDER" then a 5-byte stamp such as "-v405" (Blender
4.5) or "-v306" (Blender 3.6). This tool reports the stamp and can rewrite it.
"""
import sys

STAMP_LEN = 5


def read_stamp(path):
    with open(path, "rb") as fh:
        head = fh.read(7 + STAMP_LEN)
    if head[:7] != b"BLENDER":
        raise SystemExit("%s: not a .blend (header %r)" % (path, head[:7]))
    return head[7:7 + STAMP_LEN]


def write_stamp(path, code):
    """code like '306' -> rewrite stamp bytes to '-v306'."""
    want = ("-v" + code).encode()
    with open(path, "r+b") as fh:
        head = fh.read(7 + STAMP_LEN)
        cur = head[7:7 + STAMP_LEN]
        fh.seek(7)
        fh.write(want)
    return cur, want


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    cmd = argv[1]
    if cmd == "read":
        for path in argv[2:]:
            print("%s -> %s" % (path, read_stamp(path).decode("ascii", "replace")))
        return 0
    if cmd == "set":
        code, path = argv[2], argv[3]
        cur, want = write_stamp(path, code)
        print("%s: %s -> %s" % (path, cur.decode(), want.decode()))
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
