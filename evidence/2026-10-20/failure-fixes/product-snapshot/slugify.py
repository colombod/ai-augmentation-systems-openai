"""Convert one text argument into an ASCII slug."""

import re
import sys


def slugify(text):
    """Replace runs of original non-ASCII-alphanumeric characters with hyphens."""
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()


def main():
    if len(sys.argv) != 2:
        print("usage: slugify.py TEXT", file=sys.stderr)
        return 2
    print(slugify(sys.argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
