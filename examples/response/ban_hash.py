#!/usr/bin/env python

import sys
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
from cbapi.response import BannedHash


def ban_hash(cb, args):
    b = cb.create(BannedHash)
    b.md5hash = args.hash
    if args.description:
        b.text = args.description
    else:
        b.text = "Banned via ban_hash.py example script"
    b.enabled = True

    try:
        b.save()
    except Exception as e:
        print("Error banning hash {0}: {1}".format(args.hash, str(e)))
    else:
        print("Hash {0} successfully banned".format(args.hash))


def main():
    parser = build_cli_parser("Add an MD5 hash to the banned hash list in Cb Response")
    parser.add_argument("-H", "--hash", help="MD5 hash of the file to ban in Cb Response", required=True)
    parser.add_argument("-d", "--description", help="Description of why the hash is banned")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    return ban_hash(cb, args)


if __name__ == "__main__":
    sys.exit(main())
