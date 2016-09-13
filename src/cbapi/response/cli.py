#!/usr/bin/env python

import argparse
import contextlib

from six import iteritems
from six.moves import input
import os
import getpass
import six
if six.PY3:
    from io import BytesIO as StringIO
else:
    from cStringIO import StringIO

from cbapi.response.rest_api import get_api_token
from six.moves.configparser import RawConfigParser


@contextlib.contextmanager
def temp_umask(umask):
    oldmask = os.umask(umask)
    try:
        yield
    finally:
        os.umask(oldmask)


def configure(opts):
    credential_path = os.path.join(os.path.expanduser("~"), ".carbonblack")
    credential_file = os.path.join(credential_path, "credentials.response")

    print("Welcome to the CbAPI.")
    if os.path.exists(credential_file):
        print("An existing credential file exists at {0}.".format(credential_file))
        resp = input("Do you want to continue and overwrite the existing configuration? [Y/N] ")
        if resp.strip().upper() != "Y":
            print("Exiting.")
            return 1

    if not os.path.exists(credential_path):
        os.makedirs(credential_path, 0o700)

    url = input("URL to the Cb Response server [https://hostname]: ")

    ssl_verify = None
    while ssl_verify not in ["Y", "N"]:
        ssl_verify = input("Use SSL/TLS certificate validation (answer 'N' if using self-signed certs) [Y/N]: ")
        ssl_verify = ssl_verify.strip().upper()

    if ssl_verify == "Y":
        ssl_verify = True
    else:
        ssl_verify = False

    token = input("API token (if unknown, leave blank): ")
    if not token:
        print("No API token provided: we will look it up using your username & password")
        username = input("Username: ")
        password = getpass.getpass("Password: ")

        print("Retrieving API token for {0}...".format(username))

        try:
            token = get_api_token(url, username, password, verify=ssl_verify)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("Could not retrieve API token: {0}".format(str(e)))
            return 1

    config = RawConfigParser()
    config.readfp(StringIO('[default]'))
    config.set("default", "url", url)
    config.set("default", "token", token)
    config.set("default", "ssl_verify", ssl_verify)
    with temp_umask(0):
        with os.fdopen(os.open(credential_file, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600), 'w') as fp:
            os.chmod(credential_file, 0o600)
            config.write(fp)
    print("Successfully wrote credentials to {0}.".format(credential_file))


command_map = {
    "configure": {
        "extra_args": {},
        "help": "Configure CbAPI",
        "method": configure
    }
}


def main(args):
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command_name", help="CbAPI subcommand")

    for cmd_name, cmd_config in iteritems(command_map):
        cmd_parser = commands.add_parser(cmd_name, help=cmd_config.get("help", None))
        for cmd_arg_name, cmd_arg_config in iteritems(cmd_config.get("extra_args", {})):
            cmd_parser.add_argument(cmd_arg_name, **cmd_arg_config)

    opts = parser.parse_args(args)
    command = command_map.get(opts.command_name)
    command_method = command.get("method", None)
    if command_method:
        return command_method(opts)
