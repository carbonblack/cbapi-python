#!/usr/bin/env python
#
import sys
from cbapi.psc.threathunter import CbThreatHunterAPI
from cbapi.psc.threathunter.models import Feed as FeedTH
from cbapi.response.models import Feed
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
from cbapi.errors import ServerError
from urllib.parse import unquote
import logging

log = logging.getLogger(__name__)


def list_feeds(cb, parser, args):
    """
    Lists the feeds in CB Response
    """
    for f in cb.select(Feed):
        for fieldname in ["id", "category", "display_name", "enabled", "provider_url", "summary", "tech_data",
                          "feed_url", "use_proxy", "validate_server_cert"]:
            print("%-20s: %s" % (fieldname, getattr(f, fieldname, "")))

        if f.username:
            for fieldname in ["username", "password"]:
                print("%-20s: %s" % (fieldname, getattr(f, fieldname, "")))

        if f.ssl_client_crt:
            for fieldname in ["ssl_client_crt", "ssl_client_key"]:
                print("%-20s: %s" % (fieldname, getattr(f, fieldname, "")))

        print("\n")


def list_reports(cb, parser, args):
    """
    Lists the reports in a feed from CB Response
    :param: id - The ID of a feed
    """
    feed = cb.select(Feed, args.id, force_init=True)
    for report in feed.reports:
        print(report)
        print("\n")


def convert_feed(cb, cb_th, parser, args):
    """
    Converts and copies a feed from CB Response to CB Threat Hunter
    :param: id - The ID of a feed from CB Response

    Requires a credentials profile for both CB Response and CB Threat Hunter
        Ensure that your credentials for CB Threat Hunter have permissions to the Feed Manager APIs
    """
    th_feed = {"feedinfo": {}, "reports": []}
    # Fetches the CB Response feed
    feed = cb.select(Feed, args.id, force_init=True)

    th_feed["feedinfo"]["name"] = feed.name
    th_feed["feedinfo"]["provider_url"] = feed.provider_url
    th_feed["feedinfo"]["summary"] = feed.summary
    th_feed["feedinfo"]["category"] = feed.category
    th_feed["feedinfo"]["access"] = "private"

    # Temporary values until refresh
    th_feed["feedinfo"]["owner"] = "org_key"
    th_feed["feedinfo"]["id"] = "id"

    # Iterates the reports in the CB Response feed
    for report in feed.reports:
        th_report = {}
        th_report["id"] = report.id
        th_report["timestamp"] = report.timestamp
        th_report["title"] = report.title
        th_report["severity"] = (report.score % 10) + 1
        if hasattr(report, "description"):
            th_report["description"] = report.description
        else:
            th_report["description"] = ""
        if hasattr(report, "link"):
            th_report["link"] = report.link
        th_report["iocs"] = {}
        if report.iocs:
            if "md5" in report.iocs:
                th_report["iocs"]["md5"] = report.iocs["md5"]
            if "ipv4" in report.iocs:
                th_report["iocs"]["ipv4"] = report.iocs["ipv4"]
            if "ipv6" in report.iocs:
                th_report["iocs"]["ipv6"] = report.iocs["ipv6"]
            if "dns" in report.iocs:
                th_report["iocs"]["dns"] = report.iocs["dns"]

            if "query" in report.iocs:
                th_report["iocs"]["query"] = []
                for query in report.iocs.get("query", []):
                    try:
                        search = query.get('search_query', "")
                        if "q=" in search:
                            params = search.split('&')
                            for p in params:
                                if "q=" in p:
                                    search = unquote(p[2:])
                        # Converts the CB Response query to CB Threat Hunter
                        th_query = cb_th.convert_query(search)
                        if th_query:
                            query["search_query"] = th_query
                            th_report["iocs"]["query"].append(query)
                    except ServerError:
                        print('Invalid query {}'.format(query.get('search_query', "")))

        th_feed["reports"].append(th_report)

    # Pushes the new feed to CB Threat Hunter
    new_feed = cb_th.create(FeedTH, th_feed)
    new_feed.save()
    print("{}\n".format(new_feed))


def main():
    parser = build_cli_parser()
    parser.add_argument("-thp", "--threatprofile", help="Threat Hunter profile", default="default")
    commands = parser.add_subparsers(help="Feed commands", dest="command_name")

    commands.add_parser("list", help="List all configured feeds")

    list_reports_command = commands.add_parser("list-reports", help="List all configured reports for a feed")
    list_reports_command.add_argument("-i", "--id", type=str, help="Feed ID")

    convert_feed_command = commands.add_parser("convert", help="Convert feed from CB Response to CB Threat Hunter")
    convert_feed_command.add_argument("-i", "--id", type=str, help="Feed ID")

    args = parser.parse_args()
    cb = get_cb_response_object(args)
    cb_th = CbThreatHunterAPI(profile=args.threatprofile)

    if args.command_name == "list":
        return list_feeds(cb, parser, args)
    if args.command_name == "list-reports":
        return list_reports(cb, parser, args)
    if args.command_name == "convert":
        return convert_feed(cb, cb_th, parser, args)


if __name__ == "__main__":
    sys.exit(main())
