#stdlib
import sys
import urllib
import hashlib
import logging
import traceback

#3rd
import socket
import select
import threading
import urllib2

#pro
from aggregator import Wait, Aggregator
from agentConfig import initialize_logging,get_config
initialize_logging('forwarder')
from daemon import Daemon
from utils.pidfile import PidFile

log = logging.getLogger(__file__)

UDP_SOCKET_TIMEOUT = 5
THREAD_SLEEP_TIMEOUT = 5

PID_NAME="forwarder-agent"
PID_DIR=None

class UdpServer(object):

    def __init__(self, recv_address, aggregator, recv_port=None):
        self.address = recv_address
        self.port = recv_port
        self.buffer_size = 1024 * 8
        self.running = False
        self.udp_sock = None
        self.aggregator = aggregator
        if recv_port is None:
            self.port = 8125


    def start(self):
        try:
            self.udp_sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

        except Exception:
            log.error("IPV4 UDP connect wrong")

        try:
            self.udp_sock.bind((self.address,long(self.port)))
        except TypeError:
            log.error("server start fail.....")
            return

        #initialization parameter
        buffer_size = self.buffer_size
        sock = [self.udp_sock]
        socket_recv = self.udp_sock.recv
        timeout = UDP_SOCKET_TIMEOUT
        select_select = select.select
        aggregator = self.aggregator

        #start service
        self.running = True
        data = None;

        while self.running:
            try:
                ready = select_select(sock,[],[],timeout)
                if ready[0]:
                    data = socket_recv(buffer_size)
                    aggregator.resolve(data)

            except (KeyboardInterrupt, SystemExit) as err:
                log.warn('received KeyboardInterrupt or SystemExit %s' % err)
                break

            except Exception as err:
                log.warn('received data fail %s' %err)
                traceback.print_exc()

    def stop(self):
        self.running = False


class Reporter(threading.Thread):

    def __init__(self,request_path,appkey,secretkey,aggregator,time):
        threading.Thread.__init__(self)
        self.request_path = request_path
        self.appkey = appkey
        self.secretkey = secretkey
        self.aggregator = aggregator
        self.time = time
        self.running = False

    def stop(self):
        log.warn('Reporter in forwarder will stop!!!')
        self.running = False

    def run(self):
        self.running = True

        while self.running:
            try:
                data = self.aggregator.outqueue()
            except Wait:
                log.debug('no data receive ,thread sleep 5s')
                self.time.sleep(THREAD_SLEEP_TIMEOUT)
                continue
            log.debug('get data and now queue size is:'+str(self.aggregator.get_queue_size()))

            try:
                time = long(self.time.time() * 1000)
                req = urllib2.Request(self.request_path,data=urllib.urlencode(data),headers=self.creat_header(data,time))
                res = urllib2.urlopen(req)
                res_data = res.read()
                log.info('return content is:%s'%res_data)
            except urllib2.URLError,e:
                log.error('connect fail reason is:%s' %e)
            except Exception,e:
                log.error('connect fail reason is:%s' %e)

            # res = requests.post(self.request_path,data=urllib.urlencode(data),headers=self.creat_header(data,time))
            # log.info('return content is%s:'%res.content)


    def creat_header(self,data,time):
        header = {"Accept": "application/json",
                    "appName": data['appName'],
                    "tc": str(time),
                    "appKey": self.appkey,
                    "sign": self.md5_encode(data,time),
                    "Content-Type": "application/x-www-form-urlencoded"}
        log.debug('header is%s:'%header)
        return header

    def md5_encode(self,data,time):
        nonSysParameters1 = ''
        dic1 = {}
        dic2 = {}
        dic1['appName'] = data['appName']
        dic2['c'] = data['c']
        param_map = [dic1,dic2]
        for index, item in enumerate(param_map):
            for k, v in item.items():
                nonSysParameters1 = nonSysParameters1 + str(k) + "=" + str(v)

        m2 = hashlib.md5(nonSysParameters1)
        request_md51 = m2.hexdigest()

        m2 = hashlib.md5(request_md51 + self.appkey + self.secretkey + str(time))
        genarateSign = m2.hexdigest()

        return genarateSign


class Fowarder(Daemon):

    def __init__(self,reporter,server,pid_file=None):
        self.server = server
        self.reporter = reporter
        pid_file = pid_file or PidFile(PID_NAME, PID_DIR).get_path()
        Daemon.__init__(self, pid_file)

    def run(self):
        self.reporter.start()

        try:
            self.server.start()
        except Exception as e:
            log.exception('server start fail:%s'%e)

        finally:
            self.reporter.stop()
            self.reporter.join() #exectue main util thread is terminated
            log.info('Fowarder stop working')

            #Todo restart


def init(config_path=None):
    time = __import__('time')

    config = get_config(cfg_path=config_path)
    recv_address = config.get('recv_address')
    recv_port = config.get('recv_port')
    request_path = config.get('linklog_url')
    appkey = config.get('api_key')
    hostname = config.get('hostname')
    ipaddress = config.get('ipaddress')
    secretkey = config.get('secret_key')
    mac = config.get('mac')
    max_queue_size = config.get('max_queue_size')

    aggregator = Aggregator(max_queue_size,hostname,ipaddress,mac)

    reporter = Reporter(request_path,appkey,secretkey,aggregator,time)

    server = UdpServer(recv_address,aggregator,recv_port)

    return reporter,server,config

def main():
    reporter, server, cnf = init()
    forwarder = Fowarder(reporter,server)
    forwarder.start()
    return 0


if __name__ == '__main__':
    sys.exit(main())






