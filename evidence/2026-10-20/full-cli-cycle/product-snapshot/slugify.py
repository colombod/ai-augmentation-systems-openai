"""Convert one text argument to an ASCII slug."""

import re
import sys


def slugify(text):
    """Replace non-ASCII-alphanumeric runs with hyphens."""
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()


def main():
    if len(sys.argv) != 2:
        print("usage: python3 slugify.py TEXT", file=sys.stderr)
        return 2
    print(slugify(sys.argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
