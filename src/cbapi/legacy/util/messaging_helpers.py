#!/usr/bin/env python
#
#The MIT License (MIT)
#
# Copyright (c) 2015 Bit9 + Carbon Black
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# -----------------------------------------------------------------------------
# Wrapper class(es) around Message Bus subscribing.
#
# last updated 2015-05-25 by Ben Johnson bjohnson@bit9.com
#

import pika
import threading
import random
import traceback
import Queue

class QueuedCbSubscriber(threading.Thread):
    """
    Pushes received messages onto a queue via a thread, and then in the process()
    function calls are made to consume_message function that the derived class
    needs to implement.
    """
    def __init__(self, cb_server_address, rmq_username, rmq_password, routing_key):
        self.q = Queue.Queue()
        self.go = True

        # in case the cb url is passed in (which is often required for API stuff),
        # try to parse out the IP/DNS information.
        # This could be cleaner and better.
        cb_server_address = cb_server_address.lower()
        if cb_server_address.startswith("https://"):
            cb_server_address = cb_server_address[8:]
        elif cb_server_address.startswith("http://"):
            cb_server_address = cb_server_address[7:]
        cb_server_address = cb_server_address.split('/')[0]


        # Set the connection parameters to connect to rabbit-server1 on port 5672
        # on the / virtual host using the username "guest" and password "guest"
        credentials = pika.PlainCredentials(rmq_username, rmq_password)
        parameters = pika.ConnectionParameters(cb_server_address,
                                               5004,
                                               '/',
                                               credentials)

        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        queue_name = self.__generate_queue_name()

        # make sure you use auto_delete so the queue isn't left filling
        # with events when this program exists.
        self.channel.queue_declare(queue=queue_name, auto_delete=True)
        self.channel.queue_bind(exchange='api.events', queue=queue_name, routing_key=routing_key)
        self.channel.basic_consume(self.__on_message, queue=queue_name)
        threading.Thread.__init__(self)

    def __generate_queue_name(self):
        """
        generates a random queue name
        """
        return str(random.randint(0,10000)) + "-" + str(random.randint(0,100000))

    def __on_message(self, channel, method_frame, header_frame, body):
        """
        Just enqueue the information so we can go back to receiving messages.
        """
        try:
            self.q.put( (channel, method_frame, header_frame, body) )
        except Exception:
            traceback.print_exc()
        finally:
            # need to make sure we ack the messages so they don't get left un-acked in the queue
            # we set multiple to true to ensure that we ack all previous messages
            channel.basic_ack(delivery_tag=method_frame.delivery_tag, multiple=True)

    def run(self):
        """
        Don't call this directory, the thread will run whatever is in this function and keep running
        until this function returns.
        """
        try:
            self.channel.start_consuming()
        except:
            traceback.print_exc()
            self.stop()
        self.connection.close()

    def process(self, poll_time_secs=1):
        """
        Start the thread and consume messages.

        This is probably what you want to call from your main thread, and this will not return
        until this is told to stop by someone calling stop() which sets self.go = False.
        """
        self.start()

        while self.go:
            try:
                (channel, method_frame, header_frame, body) = self.q.get(timeout=poll_time_secs)
                self.consume_message(channel, method_frame, header_frame, body)
            except Queue.Empty:
                continue

    def stop(self, wait=True):
        try:
            self.channel.stop_consuming()
            self.go = False
            self.on_stop()
        except:
            traceback.print_exc()

        if wait:
            self.join()

    def on_stop(self):
        """
        Meant to be overrided by subclass (optional)
        """
        return

    def consume_message(self, channel, method_frame, header_frame, body):
        raise Exception("Subclass must override!")