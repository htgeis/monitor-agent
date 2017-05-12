# stdlib
from time import time
import re

#proj
import checks.system.unix as u
from checks import Check

#Check interval
INTERVAL = 30


class ServerPlugin(Check):
    def __init__(self):
        self.name='server'
        self.frequency = INTERVAL
        Check.__init__(self,self.name)
        self.check_list=(u.Cpu(),u.Memory(),u.Load(),u.Disk()) #u.IO() not useful now

    def check(self, agentConfig=None):
        data={}
        startTime = time()
        agentConfig = agentConfig or {}

        for check in self.check_list:
            status = check.check(agentConfig)
            if isinstance(status, bool) and status==False:
                self.log.warn("cehck {0} status failed".format(check.__name__))
            self.log.debug("status {0}".format(status))
            if status and isinstance(status,dict):
                for k,v in status.items():
                    if isinstance(v,float):
                        v = "%.4f" % v
                        status[k]=v
                data.update(status)

        #endTime = time()
        data['createdTime']=long(startTime*1000)
        data['appName']=self.name
        return data