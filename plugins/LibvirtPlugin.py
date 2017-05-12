from __future__ import division
from time import time
from xml import dom
from xml.dom import minidom

from checks import Check

#3rd
import libvirt
SOURCE_DES = 'qemu:///system'

#monitor parameters
SERVER_IP = 'vm_ipaddress'
SERVER_MAC = 'vm_mac'
CPU_RATE = 'cpu_rate'
CPU_RATE = 'cpu_rate'
NET_READ_RATE = 'net_read_rate'
NET_WRITE_RATE = 'net_write_rate'
DISK_READ_RATE = 'disk_read_rate'
DISK_WRITE_RATE = 'disk_write_rate'

PERCENT = 1
NANO_TO_MS = 1000000
S_TO_MS = 1000
#check interval(S)
INTERVAL = 60


class LibvirtPlugin(Check):
    def __init__(self):
        self.conn = self.creatConn()
        self.name = 'libvirt'
        self.frequency = INTERVAL
        Check.__init__(self,self.name)

    def creatConn(self):
        conn = libvirt.open(SOURCE_DES)
        if (conn == None):
            self.log.warn('fail to open connection to qemu')
            exit(0)
        return conn

    def closeConn(self):
        self.conn.close()

    def check(self,agentConfig=None,monitorData=None):
        self.conn = self.creatConn()
        response = []
        domainIDs = self.conn.listDomainsID()
        if domainIDs is None:
            self.log.warn('fail to get domainIDS')
            exit(1)
        if len(domainIDs) == 0:
            self.log.info('this host do not hvae domains')
            exit(1)

        self.log.debug('monitorData: %s'%monitorData)

        for domainID in domainIDs:
            domain_mess = {}
            basic_mess = {}

            # get past data from monitorData
            cpu_time_past = monitorData.get(CPU_RATE)
            # self.log.info('cpu_time_past: %s'%cpu_time_past)

            net_read_past = monitorData.get(NET_READ_RATE)
            # self.log.info('net_read_past: %s'%net_read_past)

            net_write_past = monitorData.get(NET_WRITE_RATE)
            # self.log.info('net_write_past: %s'%net_write_past)

            disk_read_past = monitorData.get(DISK_READ_RATE)
            # self.log.info('disk_read_past: %s'%disk_read_past)

            disk_write_past = monitorData.get(DISK_WRITE_RATE)
            # self.log.info('disk_write_past: %s'%disk_write_past)


            startTime = time()
            domain_mess['createdTime'] = long(startTime * 1000)
            domain_mess['appName'] = self.name

            domain = self.conn.lookupByID(domainID)
            domain_mess['vm_uuid'] = domain.name().split('-',1)[0]
            self.getBasicMess(basic_mess,domain_mess,domain)

            #get all rate and update past data
            cpu_time_cur = self.getCPURate(domain_mess,domain,cpu_time_past)
            net_read_cur,net_write_cur = self.getNetWorkIORate(basic_mess,domain_mess,domain,net_read_past,net_write_past)
            disk_read_cur,disk_write_cur = self.getDiskIORate(basic_mess,domain_mess,domain,disk_read_past,disk_write_past)


            monitorData[CPU_RATE] = cpu_time_cur
            monitorData[NET_READ_RATE] = net_read_cur
            monitorData[NET_WRITE_RATE] = net_write_cur
            monitorData[DISK_READ_RATE] = disk_read_cur
            monitorData[DISK_WRITE_RATE] = disk_write_cur


            #save the mess to send
            self.log.debug('domain_mess: %s'%domain_mess)
            response.append(domain_mess)

        self.log.debug('changed monitorData: %s' % monitorData)

        return monitorData,response

    def getDiskIORate(self,basic_mess,domain_mess,domain,disk_read_past,disk_write_past):
        if basic_mess.get('system_disk') is None:
            self.log.warning('this domain do not have system_disk dev')
            return disk_read_past,disk_write_past

        stats = domain.blockStats(basic_mess.get('system_disk'))

        readBytes = stats[1]
        writeBytes = stats[3]

        if disk_read_past.get(domain.name()) is None or disk_write_past.get(domain.name()) is None:
            disk_read_past[domain.name()] = readBytes
            disk_write_past[domain.name()] = writeBytes
            disk_read_rate = 0
            disk_write_rate = 0
        else:
            disk_read_rate = (readBytes - disk_read_past[domain.name()]) / INTERVAL
            disk_write_rate = (writeBytes - disk_write_past[domain.name()]) / INTERVAL
            disk_read_past[domain.name()] = readBytes
            disk_write_past[domain.name()] = writeBytes

        #save the rate
        domain_mess[DISK_READ_RATE] = disk_read_rate
        domain_mess[DISK_WRITE_RATE] = disk_write_rate

        return disk_read_past,disk_write_past



    def getNetWorkIORate(self,basic_mess,domain_mess,domain,net_read_past,net_write_past):
        if basic_mess.get('interface') is None:
            self.log.warning('this domain do not have network dev')
            return net_read_past,net_write_past

        stats = domain.interfaceStats(basic_mess.get('interface'))

        readBytes = stats[0]
        writeBytes = stats[4]


        if net_read_past.get(domain.name()) is None or net_write_past.get(domain.name()) is None:
            net_read_past[domain.name()] = readBytes
            net_write_past[domain.name()] = writeBytes
            net_read_rate = 0
            net_write_rate = 0
        else:
            net_read_rate = (readBytes - net_read_past[domain.name()]) / INTERVAL
            net_write_rate = (writeBytes - net_write_past[domain.name()]) / INTERVAL
            net_read_past[domain.name()] = readBytes
            net_write_past[domain.name()] = writeBytes

        #save the rate
        domain_mess[NET_READ_RATE] = net_read_rate
        domain_mess[NET_WRITE_RATE] = net_write_rate

        return net_read_past,net_write_past


    def getCPURate(self,domain_mess,domain,cpu_time_past):
        time_data = domain.getCPUStats(1,0)[0]
        cpu_time = time_data.get('cpu_time')
        if cpu_time_past.get(domain.name()) is None:
            cpu_time_past[domain.name()] = cpu_time
            cpu_rate = 0
        else:
            cpu_rate = (cpu_time - cpu_time_past[domain.name()])*PERCENT / NANO_TO_MS / (INTERVAL * S_TO_MS)
            cpu_time_past[domain.name()] = cpu_time

        domain_mess[CPU_RATE] = cpu_rate
        return cpu_time_past


    def getBasicMess(self,basic_mess,domain_mess,domain):

        raw_xml = domain.XMLDesc(0)
        xml = minidom.parseString(raw_xml)

        interfaceTypes = xml.getElementsByTagName('interface')
        for interfaceType in interfaceTypes:
            if interfaceType.getElementsByTagName('ip'):
                try:
                    domain_mess[SERVER_IP] = interfaceType.getElementsByTagName('ip')[0].getAttribute('address')
                    domain_mess[SERVER_MAC] = interfaceType.getElementsByTagName('mac')[0].getAttribute('address')
                    basic_mess['interface'] = interfaceType.getElementsByTagName('target')[0].getAttribute('dev')
                    print basic_mess['interface']
                except IndexError as err:
                    self.log.warn('interface xml do not have needed message %s' % err)

        diskTypes = xml.getElementsByTagName('disk')
        for diskType in diskTypes:
            if diskType.getElementsByTagName('target')[0].getAttribute('dev') == 'vda' or 'hda':
                try:
                    basic_mess['system_disk'] = diskType.getElementsByTagName('target')[0].getAttribute('dev')
                except IndexError as err:
                    self.log.warn('disk xml do not have needed message %s' % err)




