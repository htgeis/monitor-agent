#stdlib
import struct
import logging
import time

# 3rd
import json
from Queue import Queue, Empty, Full

# proj
#from agentConfig import initialize_logging
from utils.serverutil import get_mac_address,get_local_ip,get_username

#initialize_logging()
log = logging.getLogger(__file__)


class Wait(Exception):
    pass


class Aggregator(object):
    def __init__(self, max_queue_size,hostname=None,ipaddress=None,mac=None):
        self.hostname = hostname
        self.ipaddress = ipaddress
        self.mac = mac
        self.max_queue = max_queue_size
        self.queue = Queue(self.max_queue)
        if self.hostname is None:
            self.hostname = get_username()
        if self.mac is None:
            self.mac = get_mac_address()
        if self.ipaddress is None:
            self.ipaddress = get_local_ip()

        log.info("mac is {0} and ip is {1}".format(self.mac,self.ipaddress))

    def resolve(self, data):
        recv_data = json.loads(data)
        log.debug('recv_data is :%s'%recv_data)
        lol_data = {}
        recv_data['hostname'] = self.hostname
        recv_data['ipaddress'] = self.ipaddress
        recv_data['mac'] = self.mac
        # trans to str
        content={}

        for k,v in recv_data.items():
            k = k.encode("utf-8")

            #del recv_data[k]
            if type(v) is not unicode:
                #v = str(v)
                v = json.dumps(v,ensure_ascii=False).encode('utf-8')
                if(v.startswith("\"")):
                    v=v.strip("\"")
            elif type(v) is unicode:
                v = v.encode("utf-8")

            content.setdefault(k, v)

        if recv_data.get('createdTime') is None:
            log.warning('createdTime is missing')
            content['createdTime'] = long(time.time() * 1000)
        if recv_data.get('appName') is None:
            log.warning('this msg don\'t contain appName and will be discarded')
            return
        else:
            lol_data['appName'] = recv_data.get('appName')

        #just for test
        #lol_data['appName'] = 'test-ping'

        #
        lol_data['c'] = [content]
        self.enqueue(lol_data)

    def enqueue(self, data):
        try:
            self.queue.put(data, block=True, timeout=5)
        except Full:
            log.error('timeout,discard data')

    def outqueue(self):
        try:
            return self.queue.get(1, 5)
        except Empty:
            raise Wait

    def get_queue_size(self):
        return self.queue.qsize()