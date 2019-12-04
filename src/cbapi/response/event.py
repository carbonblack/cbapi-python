#!/usr/bin/env python

from __future__ import absolute_import
from ..event import registry
from ..errors import CredentialError
import pika
import platform
import os
import threading
import logging
import json
from time import sleep

from cbapi.six.moves import SimpleHTTPServer, BaseHTTPServer
from cbapi.six.moves import urllib

import ssl


log = logging.getLogger(__name__)


class FileEventSource(threading.Thread):
    def __init__(self, cb, filename):
        super(FileEventSource, self).__init__()
        self.daemon = True

        self._done = False
        self._cb = cb

        self._fp = open(filename, "rb")
        log.debug("Opened %s" % filename)

    def run(self):
        while not self._fp.closed:
            line = self._fp.readline()
            if line == "":
                # wait for new events
                sleep(1)
                continue

            try:
                msg = json.loads(line)
                routing_key = msg.get("type")
                # log.debug("Received message with routing key %s" % routing_key)
                registry.eval_callback(routing_key, line, self._cb)
            except Exception:
                pass

    def stop(self):
        self._fp.close()


class EventForwarderHTTPSource(threading.Thread):
    def __init__(self, cb, listening_address, **kwargs):
        super(EventForwarderHTTPSource, self).__init__()
        self.daemon = True

        http_parts = urllib.parse.urlparse(listening_address)
        addr_parts = http_parts.netloc.split(":")
        listening_host = addr_parts[0]
        if len(addr_parts) == 2:
            port = int(addr_parts[1])
            listening_host = addr_parts[0]
        else:
            if http_parts.scheme == "https":
                port = 443
            else:
                port = 80

        self.listening_address = listening_address
        self.httpd = BaseHTTPServer.HTTPServer((listening_host, port), SimpleHTTPServer.SimpleHTTPRequestHandler)

        if http_parts.scheme == "https":
            keyfile = kwargs.get("keyfile", None)
            certfile = kwargs.get("certfile", None)
            if not keyfile or not certfile:
                raise CredentialError("Need to specify 'keyfile' and 'certfile' for HTTPS")
            self.httpd.socket = ssl.wrap_socket(self.httpd.socket, certfile=certfile, keyfile=keyfile,
                                                server_side=True)

    def run(self):
        self.httpd.serve_forever()


# This class is based on the pika asynchronous consumer example at
# http://pika.readthedocs.io/en/0.10.0/examples/asynchronous_consumer_example.html

class RabbitMQEventSource(threading.Thread):
    def __init__(self, cb):
        super(RabbitMQEventSource, self).__init__()
        self.daemon = True

        self._closing = False
        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._auto_ack = True
        self._consuming = False

        self._cb = cb
        creds = cb.credentials

        if not creds.rabbitmq_pass:
            error_text = "RabbitMQEventSource requires credentials for the event bus. Make sure that\n" + \
                         "rabbitmq_pass, rabbitmq_user, rabbitmq_host, and rabbitmq_port are defined\n" + \
                         "in the credential file"

            if cb.credential_profile_name:
                error_text += " for profile '{0}'.".format(cb.credential_profile_name)

            raise CredentialError(error_text)

        self._url = "amqp://{0}:{1}@{2}:{3}".format(creds.rabbitmq_user, creds.rabbitmq_pass, creds.rabbitmq_host,
                                                    creds.rabbitmq_port)

        self.QUEUE = "cbapi-event-handler-{0}-{1}".format(platform.uname()[1], os.getpid())
        self.EXCHANGE = "api.events"
        self.ROUTING_KEYS = registry.event_types
        self.EXCHANGE_TYPE = "topic"

    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.

        :rtype: pika.SelectConnection

        """
        log.debug('Connecting to %s', self._url)
        return pika.SelectConnection(pika.URLParameters(self._url),
                                     self.on_connection_open,
                                     stop_ioloop_on_close=False)

    def on_connection_open(self, unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.

        :type unused_connection: pika.SelectConnection

        """
        log.debug('Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def add_on_connection_close_callback(self):
        """This method adds an on close callback that will be invoked by pika
        when RabbitMQ closes the connection to the publisher unexpectedly.

        """
        log.debug('Adding connection close callback')
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given

        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            log.warning('Connection closed, reopening in 5 seconds: (%s) %s',
                        reply_code, reply_text)
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is
        closed. See the on_connection_closed method.

        """
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        if not self._closing:

            # Create a new connection
            self._connection = self.connect()

            # There is now a new connection, needs a new ioloop to run
            self._connection.ioloop.start()

    def open_channel(self):
        """Open a new channel with RabbitMQ by issuing the Channel.Open RPC
        command. When RabbitMQ responds that the channel is open, the
        on_channel_open callback will be invoked by pika.

        """
        log.debug('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.

        Since the channel is now open, we'll declare the exchange to use.

        :param pika.channel.Channel channel: The channel object

        """
        log.debug('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if
        RabbitMQ unexpectedly closes the channel.

        """
        log.debug('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed

        """
        log.warning('Channel %i was closed: (%s) %s',
                    channel, reply_code, reply_text)
        self._connection.close()

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC
        command. When it is complete, the on_exchange_declareok method will
        be invoked by pika.

        :param str|unicode exchange_name: The name of the exchange to declare

        """
        log.debug('Declaring exchange %s', exchange_name)
        self._channel.exchange_declare(self.on_exchange_declareok,
                                       exchange_name,
                                       self.EXCHANGE_TYPE,
                                       durable=True,
                                       auto_delete=False)

    def on_exchange_declareok(self, unused_frame):
        """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC
        command.

        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame

        """
        log.debug('Exchange declared')
        self.setup_queue(self.QUEUE)

    def setup_queue(self, queue_name):
        """Setup the queue on RabbitMQ by invoking the Queue.Declare RPC
        command. When it is complete, the on_queue_declareok method will
        be invoked by pika.

        :param str|unicode queue_name: The name of the queue to declare.

        """
        log.debug('Declaring queue %s', queue_name)
        self._channel.queue_declare(self.on_queue_declareok, queue_name, auto_delete=True)

    def on_queue_declareok(self, method_frame):
        """Method invoked by pika when the Queue.Declare RPC call made in
        setup_queue has completed. In this method we will bind the queue
        and exchange together with the routing key by issuing the Queue.Bind
        RPC command. When this command is complete, the on_bindok method will
        be invoked by pika.

        :param pika.frame.Method method_frame: The Queue.DeclareOk frame

        """
        for routing_key in self.ROUTING_KEYS:
            log.debug('Binding %s to %s with %s',
                      self.EXCHANGE, self.QUEUE, routing_key)
            self._channel.queue_bind(self.on_bindok, self.QUEUE,
                                     self.EXCHANGE, routing_key)

    def on_bindok(self, unused_frame):
        """Invoked by pika when the Queue.Bind method has completed. At this
        point we will start consuming messages by calling start_consuming
        which will invoke the needed RPC commands to start the process.

        :param pika.frame.Method unused_frame: The Queue.BindOk response frame

        """
        log.debug('Queue bound')
        self.start_consuming()

    def start_consuming(self):
        """This method sets up the consumer by first calling
        add_on_cancel_callback so that the object is notified if RabbitMQ
        cancels the consumer. It then issues the Basic.Consume RPC command
        which returns the consumer tag that is used to uniquely identify the
        consumer with RabbitMQ. We keep the value to use it when we want to
        cancel consuming. The on_message method is passed in as a callback pika
        will invoke when a message is fully received.

        """
        if not self._consuming:
            log.debug('Issuing consumer related RPC commands')
            self.add_on_cancel_callback()
            self._consumer_tag = self._channel.basic_consume(self.on_message,
                                                             self.QUEUE, no_ack=self._auto_ack)
            self._consuming = True

    def add_on_cancel_callback(self):
        """Add a callback that will be invoked if RabbitMQ cancels the consumer
        for some reason. If RabbitMQ does cancel the consumer,
        on_consumer_cancelled will be invoked by pika.

        """
        log.debug('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame

        """
        log.debug('Consumer was cancelled remotely, shutting down: %r',
                  method_frame)
        if self._channel:
            self._channel.close()

    def acknowledge_message(self, delivery_tag):
        """Acknowledge the message delivery from RabbitMQ by sending a
        Basic.Ack RPC method for the delivery tag.

        :param int delivery_tag: The delivery tag from the Basic.Deliver frame

        """
        log.debug('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def stop_consuming(self):
        """Tell RabbitMQ that you would like to stop consuming by sending the
        Basic.Cancel RPC command.

        """
        if self._channel:
            log.debug('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def on_cancelok(self, unused_frame):
        """This method is invoked by pika when RabbitMQ acknowledges the
        cancellation of a consumer. At this point we will close the channel.
        This will invoke the on_channel_closed method once the channel has been
        closed, which will in-turn close the connection.

        :param pika.frame.Method unused_frame: The Basic.CancelOk frame

        """
        log.debug('RabbitMQ acknowledged the cancellation of the consumer')
        self.close_channel()

    def close_channel(self):
        """Call to close the channel with RabbitMQ cleanly by issuing the
        Channel.Close RPC command.

        """
        log.debug('Closing the channel')
        self._channel.close()

    def run(self):
        """Run the example consumer by connecting to RabbitMQ and then
        starting the IOLoop to block and allow the SelectConnection to operate.

        """
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Cleanly shutdown the connection to RabbitMQ by stopping the consumer
        with RabbitMQ. When RabbitMQ confirms the cancellation, on_cancelok
        will be invoked by pika, which will then closing the channel and
        connection. The IOLoop is started again because this method is invoked
        when CTRL-C is pressed raising a KeyboardInterrupt exception. This
        exception stops the IOLoop which needs to be running for pika to
        communicate with RabbitMQ. All of the commands issued prior to starting
        the IOLoop will be buffered but not processed.

        """
        log.debug('Stopping')
        self._closing = True
        self.stop_consuming()
        self._connection.ioloop.stop()
        log.debug('Stopped')

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        log.debug('Closing connection')
        self._connection.close()

    def on_message(self, unused_channel, basic_deliver, properties, body):
        """Invoked by pika when a message is delivered from RabbitMQ. The
        channel is passed for your convenience. The basic_deliver object that
        is passed in carries the exchange, routing key, delivery tag and
        a redelivered flag for the message. The properties passed in is an
        instance of BasicProperties with the message properties and the body
        is the message that was sent.

        :param pika.channel.Channel unused_channel: The channel object
        :param pika.Spec.Basic.Deliver: basic_deliver method
        :param pika.Spec.BasicProperties: properties
        :param str|unicode body: The message body

        """
        log.debug('Received message # %s with properties %s',
                  basic_deliver.delivery_tag, properties)

        registry.eval_callback(basic_deliver.routing_key, body, self._cb)

        if not self._auto_ack:
            self.acknowledge_message(basic_deliver.delivery_tag)
