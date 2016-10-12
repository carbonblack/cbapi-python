import argparse
from cbapi.response import CbEnterpriseResponseAPI
from cbapi.protection import CbEnterpriseProtectionAPI
import codecs
import sys


# Example scripts: we want to make sure that sys.stdout is using utf-8 encoding. See issue #36.
sys.stdout = codecs.getwriter('utf8')(sys.stdout)


def build_cli_parser(description="Cb Example Script"):
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("--cburl", help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_argument("--apitoken", help="API Token for Carbon Black server")
    parser.add_argument("--no-ssl-verify", help="Do not verify server SSL certificate.", action="store_true",
                        default=False)
    parser.add_argument("--profile", help="profile to connect", default="default")
    parser.add_argument("--verbose", help="enable debug logging", default=False, action='store_true')

    return parser


def disable_insecure_warnings():
    import requests.packages.urllib3
    requests.packages.urllib3.disable_warnings()


def get_cb_response_object(args):
    if args.verbose:
        import logging
        logging.basicConfig()
        logging.getLogger("cbapi").setLevel(logging.DEBUG)
        logging.getLogger("__main__").setLevel(logging.DEBUG)

    if args.cburl and args.apitoken:
        cb = CbEnterpriseResponseAPI(url=args.cburl, token=args.apitoken, ssl_verify=(not args.no_ssl_verify))
    else:
        cb = CbEnterpriseResponseAPI(profile=args.profile)

    return cb


def get_cb_protection_object(args):
    if args.verbose:
        import logging
        logging.basicConfig()
        logging.getLogger("cbapi").setLevel(logging.DEBUG)
        logging.getLogger("__main__").setLevel(logging.DEBUG)

    if args.cburl and args.apitoken:
        cb = CbEnterpriseProtectionAPI(args.cburl, args.apitoken)
    else:
        cb = CbEnterpriseProtectionAPI(profile=args.profile)

    return cb


def get_object_by_name_or_id(cb, cls, name_field="name", id=None, name=None, force_init=True):
    clsname = cls.__name__
    try:
        if id:
            attempted_to_find = "ID of {0:d}".format(id)
            objs = [cb.select(cls, id, force_init=force_init)]
        else:
            attempted_to_find = "name {0:s}".format(name)
            objs = cb.select(cls).where("{0}:{1}".format(name_field, name))[::]
            if not len(objs):
                raise Exception("No {0}s match".format(clsname))
    except Exception as e:
        raise Exception("Could not find {0} with {1:s}: {2:s}".format(clsname, attempted_to_find, str(e)))
    else:
        return objs
