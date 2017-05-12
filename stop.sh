#!/bin/sh
# monitor-agent stop script

cur="$(cd `dirname $0`; pwd)"
collector_pid_file="$cur"/run/collector-agent.pid
isCollectorKilled=false
if [ -f $collector_pid_file ];then
    pid=`cat $collector_pid_file`
    echo "get pid $pid"
    if [ -n pid ];then
       ps -ef|grep $pid|grep "collector.py"
       if [ $? -eq 0 ];then
           echo "find process collector pid in pid_file and collector is killing now"
           kill -9 $pid
           isCollectorKilled=true
       fi
    fi
fi
forwarder_pid_file="$cur"/run/forwarder-agent.pid
isForwarderKilled=false
if [ -f $forwarder_pid_file ];then
    pid=`cat $forwarder_pid_file`
    if [ -n pid ];then
       ps -ef|grep $pid|grep "forwarder.py"
       if [ $? -eq 0 ];then
           echo "find process forwarder pid in pid_file and forwarder is killing now"
           kill -9 $pid
           isForwarderKilled=true
       fi
    fi
fi
if ! $isCollectorKilled
then
    echo "pidfile not contains the right pid for collector, this thread will killed forced by ps-ef search"
    pid=$(ps -ef|grep "collector.py"|grep -v "grep"|awk '{print $2}')
    if [ "$pid" ];then
        kill -9 $pid
    fi
fi
if ! $isForwarderKilled
then
    echo "pidfile not contains the right pid for forwarder, this thread will killed forced by ps-ef search"
    pid=$(ps -ef|grep "forwarder.py"|grep -v "grep"|awk '{print $2}')
    if [ "$pid" ];then
        kill -9 $pid
    fi
fi
