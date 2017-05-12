
# stdlib
import logging
import os
import signal
import sys
import time

#proj
import agentConfig
agentConfig.initialize_logging('collector')
from utils.pidfile import PidFile
from utils.util import Timer
from utils.pluginUtil import get_plugin_class
from utils.sendutil import Sender
from daemon import Daemon

# Globals
log = logging.getLogger('collector')
PID_NAME = "collector-agent"
PID_DIR = None

CPU_RATE = 'cpu_rate'
NET_READ_RATE = 'net_read_rate'
NET_WRITE_RATE = 'net_write_rate'
DISK_READ_RATE = 'disk_read_rate'
DISK_WRITE_RATE = 'disk_write_rate'

# Global Monitor message
monitor_data_past = {CPU_RATE:{},NET_READ_RATE:{},NET_WRITE_RATE:{},DISK_READ_RATE:{},DISK_WRITE_RATE:{}}



class Agent(Daemon):
    def __init__(self,pidfile=None):
        pidfile = pidfile or PidFile(PID_NAME, PID_DIR).get_path()
        Daemon.__init__(self,pidfile)
        self.basic_plugin=['ServerPlugin']
        config=agentConfig.get_config()
        self.sender = Sender(port=config['recv_port'])
        self.check_frequency=config['check_freq']

    def run(self):
        global monitor_data_past

        timer = Timer()

        plugins={}

        count={}

        for pluginName in self.basic_plugin:
            Plugin=get_plugin_class(pluginName)
            plugin=Plugin()
            plugins[pluginName]=plugin
            count[pluginName]=plugin.frequency/self.check_frequency

        for pluginName in self.get_run_plugins():
            Plugin=get_plugin_class(pluginName)
            plugin=Plugin()
            plugins[pluginName]=plugin
            count[pluginName]=plugin.frequency/self.check_frequency

        while(self.run_forever):
            timer.start()

            #do check
            for name,plugin in plugins.items():
                if count[name] != 1:
                    count[name] = count[name] - 1
                else:
                    count[name] = plugin.frequency/self.check_frequency
                    if name == 'LibvirtPlugin':
                        monitor_data_cur,data=plugin.check(monitorData=monitor_data_past)
                        monitor_data_past = monitor_data_cur
                    else:
                        data=plugin.check()
                    log.debug("check "+name+" get:"+str(data))

                    if isinstance(data, list):
                        for datanode in data:
                            self.sender.emit(datanode)
                    else:
                        self.sender.emit(data)

            cost=timer.total()
            if cost > self.check_frequency:
                log.warn("collect metrics cost time {0} is longer than check_frequency {1}".format(cost, self.check_frequency))
            else:
                log.debug("sleep {0}s for next loop".format(self.check_frequency - cost))
                time.sleep(self.check_frequency - cost)

    def get_run_plugins(self):
        config = agentConfig.get_config()
        return config.get("run_plugins",[])


def main():
    options, args = agentConfig.get_parsed_args()
    #config = agentConfig.get_config(options=options)

    COMMANDS_AGENT = [
        'start',
        'stop',
        'restart',
        'status',
        'foreground',
    ]

    COMMANDS=COMMANDS_AGENT

    if len(args)==0:
        args=['start']

    if len(args) < 1:
        sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], "|".join(COMMANDS)))
        return 2

    command = args[0]
    if command not in COMMANDS:
        sys.stderr.write("Unknown command:%s \n" % command)
        return 3

    if command in COMMANDS_AGENT:
        pass
    agent = Agent(PidFile(PID_NAME, PID_DIR).get_path())

    if 'start' == command:
        log.info('Start daemon')
        agent.start()

    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except StandardError:
        try:
            log.exception("Uncaught error running the Agent")
        except Exception:
            pass
        raise