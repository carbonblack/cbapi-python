#!/usr/bin/env python

from cbapi.response.models import Binary
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import sys
from six.moves.queue import Queue
import os
import threading
import json

import logging

worker_queue = Queue(maxsize=50)


def get_path_for_md5(d, basepath=''):
    d = d.upper()
    return os.path.join(basepath, d[:3], d[3:6], d)


def create_directory(pathname):
    try:
        os.makedirs(os.path.dirname(pathname))
    except:
        pass


class BinaryWorker(threading.Thread):
    def __init__(self, basepath):
        self.basepath = basepath
        threading.Thread.__init__(self)

    def already_exists(self, pathname, item):
        try:
            filesize = os.path.getsize(pathname)
            if filesize == item.copied_size:
                return True
        except:
            pass

        return False

    def run(self):
        l = logging.getLogger(__name__)
        l.setLevel(logging.INFO)

        while True:
            item = worker_queue.get()
            pathname = get_path_for_md5(item.md5sum, self.basepath)

            if self.already_exists(pathname, item):
                l.info('already have %s' % item.md5sum)
            else:
                create_directory(pathname)
                write_progress = 0
                try:
                    open(pathname, 'wb').write(item.file.read())
                    write_progress += 1
                    json.dump(item.original_document, open(pathname + '.json', 'w'))
                    write_progress += 1
                except:
                    pass

                if not write_progress:
                    l.error(u'Could not grab {0:s}'.format(item.md5sum))
                elif write_progress == 1:
                    l.info(u'Grabbed {0:s} binary'.format(item.md5sum))
                elif write_progress == 2:
                    l.info(u'Grabbed {0:s} binary & process document'.format(item.md5sum))
            worker_queue.task_done()


def dump_all_binaries(cb, destdir, start):
    threads = []
    num_worker_threads = 10
    for i in range(num_worker_threads):
        t = BinaryWorker(destdir)
        t.daemon = True
        t.start()
        threads.append(t)

    for binary in cb.select(Binary).all():
        worker_queue.put(binary)

    worker_queue.join()


def main():
    parser = build_cli_parser("Grab all binaries from a Cb server")
    parser.add_argument('-d', '--destdir', action='store', help='Destination directory to place the events',
                        default=os.curdir)

    # TODO: we don't have a control on the "start" value in the query yet
    # parser.add_argument('--start', action='store', dest='startvalue', help='Start from result number', default=0)
    parser.add_argument('-v', action='store_true', dest='verbose', help='Enable verbose debugging messages',
                        default=False)
    args = parser.parse_args()

    cb = get_cb_response_object(args)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # startvalue = args.startvalue
    startvalue = 0
    return dump_all_binaries(cb, args.destdir, startvalue)


if __name__ == '__main__':
    sys.exit(main())

