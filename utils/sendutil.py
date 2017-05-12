#!/usr/bin/env python

import logging
import socket
import json
try:
    from itertools import imap
except ImportError:
    imap = map


log = logging.getLogger(__file__)


class Sender(object):

    def __init__(self, host='localhost', port=8225):
        self.host = host
        self.port = int(port)
        self.socket = None
        self._send = self._send_to_server
        self.encoding = 'utf-8'
        log.info("initial Sender to forwarder in port:"+str(port))

    def get_socket(self):
        """
        Return a connected socket.
        Note: connect the socket before assigning it to the class instance to
        avoid bad thread race conditions.
        """
        if not self.socket:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect((self.host, self.port))
            self.socket = sock
        return self.socket

    def emit(self,dic):
        """
        emit message with dic type
        """
        data = json.dumps(dic,ensure_ascii=False)
        self._send(data)

    def _send_to_server(self, packet):
        try:
            # If set, use socket directly
            (self.socket or self.get_socket()).send(packet.encode(self.encoding))
        except socket.error:
            log.info("Error submitting packet, will try refreshing the socket")
            self.socket = None
            try:
                self.get_socket().send(packet.encode(self.encoding))
            except socket.error:
                log.exception("Failed to send packet with a newly binded socket")

sender = Sender()