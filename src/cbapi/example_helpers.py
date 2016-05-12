import argparse
from cbapi.response import CbEnterpriseResponseAPI
from cbapi.protection import CbEnterpriseProtectionAPI


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
        cb = CbEnterpriseResponseAPI(args.cburl, args.apitoken)
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
