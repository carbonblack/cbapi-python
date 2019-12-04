import boto3
import json
import time
from cbapi.response.models import BannedHash
from cbapi.example_helpers import build_cli_parser, get_cb_response_object

processed_list = set()

cb = None
watchlist_name = None


def process_events(data):
    #
    # Split on newline
    #
    for event in data.split('\n'):
        if not event:
            continue

        #
        # Load the event as json
        #
        event_json = json.loads(event)

        #
        # Check for watchlist event type
        #
        if event_json.get('type', '') == "watchlist.hit.process" or \
                event_json.get('type', '') == "watchlist.hit.binary":
            #
            # Check if matches our watchlist_name
            #
            md5sum = event_json.get('docs', [])[0].get('process_md5', '')
            if event_json.get('watchlist_name', '').lower() == watchlist_name.lower():
                print("[+]: Banning Hash: {}".format(md5sum))

                try:
                    bh = cb.create(BannedHash)
                    bh.md5hash = md5sum
                    bh.text = "Auto-Blacklist from s3-watchlist-ban.py"
                    bh.save()
                    print(bh)
                except Exception as e:
                    print(e.message)


def save_progress(processed_list):
    #
    # Save our progress in a log file
    #
    with open('script_progress.log', 'wb') as hfile:
        hfile.write(json.dumps(list(processed_list)))


def listen_mode(bucket):

    print("[+]: Listen Mode")

    #
    # Init Set with all current files
    #
    current_list = set()
    for obj in bucket.objects.all():
        key = obj.key
        current_list.add(key)

    #
    # Infinite loop and we only process new files we see
    #
    while True:
        for obj in bucket.objects.all():
            key = obj.key
            if key not in current_list:
                print("[+]: New File: {}".format(key))
                #
                # We have not processed this file.
                #
                body = obj.get()['Body'].read()
                process_events(body)
                current_list.add(key)
            else:
                pass

        print("Sleeping for 1 min")
        time.sleep(60)


if __name__ == "__main__":
    print("Starting s3-watchlist-ban script...")
    #
    # Argument parsing
    #
    parser = build_cli_parser()
    parser.add_argument("-w", '--watchlist',
                        help="Watchlist Name",
                        required=True)

    parser.add_argument("-b", '--bucket',
                        help="S3 Bucket Name",
                        required=True)

    parser.add_argument("-a", '--awsprofile',
                        help="AWS Credential profile",
                        required=False)

    parser.add_argument("-l", '--listen',
                        help="Listen mode and only process new events",
                        action='store_true',
                        required=False)

    args = parser.parse_args()

    if not args.profile:
        aws_profile = "default"
    else:
        aws_profile = args.awsprofile

    #
    # Connect to S3
    #
    session = boto3.Session(profile_name=aws_profile)
    s3 = session.resource('s3')
    my_bucket = s3.Bucket(args.bucket)

    #
    # Connect to Cb Response so we can create Banned Hashes
    #
    cb = get_cb_response_object(args)

    #
    # Save watchlist name from arguments
    #
    watchlist_name = args.watchlist

    if args.listen:
        listen_mode(my_bucket)

    try:
        with open('script_progress.log', 'rb') as hfile:
            for item in json.loads(hfile.read()):
                processed_list.add(item)
    except Exception:
        print("[?]: No previous progress file found: script_progress.log")
        processed_list = set()

    #
    # List all files in S3 Bucket
    #
    for obj in reversed(list(my_bucket.objects.all())):
        key = obj.key

        #
        # Check to see if we have already processed this file
        #
        if key not in processed_list:
            print("[+]: Processing file: {}".format(key))
            #
            # We have not processed this file.
            #
            body = obj.get()['Body'].read()

            process_events(body)
            processed_list.add(key)
            save_progress(processed_list)
        else:
            print("[+]: We have already processed file: {}".format(key))

    print("[+]: saving progess to file script_progress.log")
    save_progress(processed_list)
