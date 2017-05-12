#coding=utf-8

# stdlib
import logging
import socket
import select
import json
import sys

# proj
import agentConfig
from utils.net import inet_pton
from utils.net import IPV6_V6ONLY, IPPROTO_IPV6

agentConfig.initialize_logging('')
log = logging.getLogger(__file__)
UDP_SOCKET_TIMEOUT = 5

class Server(object):
    """
    A statsd udp server.
    """
    def __init__(self, host, port, forward_to_host=None, forward_to_port=None):
        self.sockaddr = None
        self.socket = None
        self.host = host
        self.port = port
        self.buffer_size = 1024 * 8

        self.running = False

        self.should_forward = forward_to_host is not None

        self.forward_udp_sock = None
        # In case we want to forward every packet received to another statsd server
        if self.should_forward:
            if forward_to_port is None:
                forward_to_port = 8225

            log.info("External statsd forwarding enabled. All packets received will be forwarded to %s:%s" % (forward_to_host, forward_to_port))
            try:
                self.forward_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.forward_udp_sock.connect((forward_to_host, forward_to_port))
            except Exception:
                log.exception("Error while setting up connection to external statsd server")

    def start(self):
        """
        Run the server.
        """
        ipv4_only = True

        if not ipv4_only:
            try:
                # Bind to the UDP socket in IPv4 and IPv6 compatibility mode
                self.socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                # Configure the socket so that it accepts connections from both
                # IPv4 and IPv6 networks in a portable manner.
                self.socket.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)
            except Exception:
                log.info('unable to create IPv6 socket, falling back to IPv4.')
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                ipv4_only = True
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.socket.setblocking(0)

        #let's get the sockaddr
        self.sockaddr = get_socket_address(self.host, int(self.port), ipv4_only=ipv4_only)

        try:
            self.socket.bind(self.sockaddr)
        except TypeError:
            log.error('Unable to start Dogstatsd server loop, exiting...')
            return

        log.info('Listening on socket address: %s', str(self.sockaddr))

        # Inline variables for quick look-up.
        buffer_size = self.buffer_size
        sock = [self.socket]
        socket_recv = self.socket.recv
        select_select = select.select
        select_error = select.error
        timeout = UDP_SOCKET_TIMEOUT
        should_forward = self.should_forward
        forward_udp_sock = self.forward_udp_sock

        # Run our select loop.
        self.running = True
        message = None
        while self.running:
            try:
                ready = select_select(sock, [], [], timeout)
                if ready[0]:
                    message = socket_recv(buffer_size)
                    submit_packets(message)

                    if should_forward:
                        forward_udp_sock.send(message)
            except select_error as se:
                # Ignore interrupted system calls from sigterm.
                errno = se[0]
                if errno != 4:
                    raise
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception:
                log.exception('Error receiving datagram `%s`', message)

    def stop(self):
        self.running = False

def mapto_v6(addr):
    """
    Map an IPv4 address to an IPv6 one.
    If the address is already an IPv6 one, just return it.
    Return None if the IP address is not valid.
    """
    try:
        inet_pton(socket.AF_INET, addr)
        return '::ffff:{}'.format(addr)
    except socket.error:
        try:
            inet_pton(socket.AF_INET6, addr)
            return addr
        except socket.error:
            log.debug('%s is not a valid IP address.', addr)

    return None

def get_socket_address(host, port, ipv4_only=False):
    """
    Gather informations to open the server socket.
    Try to resolve the name giving precedence to IPv4 for retro compatibility
    but still mapping the host to an IPv6 address, fallback to IPv6.
    """
    try:
        info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)
    except socket.gaierror as e:
        try:
            if not ipv4_only:
                info = socket.getaddrinfo(host, port, socket.AF_INET6, socket.SOCK_DGRAM)
            elif host == 'localhost':
                log.warning("Warning localhost seems undefined in your host file, using 127.0.0.1 instead")
                info = socket.getaddrinfo('127.0.0.1', port, socket.AF_INET, socket.SOCK_DGRAM)
            else:
                log.error('Error processing host %s and port %s: %s', host, port, e)
                return None
        except socket.gaierror as e:
            log.error('Error processing host %s and port %s: %s', host, port, e)
            return None

    # we get the first item of the list and map the address for IPv4 hosts
    sockaddr = info[0][-1]
    if info[0][0] == socket.AF_INET and not ipv4_only:
        mapped_host = mapto_v6(sockaddr[0])
        sockaddr = (mapped_host, sockaddr[1], 0, 0)
    return sockaddr


def submit_packets(packets,utf8_decoding=True):
    if utf8_decoding:
        packets = unicode(packets, 'utf-8', errors='replace')
    log.info("revice packets len:"+str(len(packets.splitlines())))
    data={}
    for packet in packets.splitlines():
        if not packet.strip():
            continue
        try:
            dd=json.loads(packet)
            if isinstance(dd,dict):
                data.update(dd)
        except json.JSONDecoder as e:
            log.warn("decode json message error :%s",e)

    log.info("get data:"+str(data))


if __name__ == '__main__':
    server = Server('127.0.0.1', '8225')
    server.start()
    log.info("server is ending!")
    sys.exit(0)
