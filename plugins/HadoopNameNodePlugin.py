import json
import logging
import urllib2
from time import time
from urlparse import urljoin

from checks import Check

# URL Paths
JMX_PATH = 'jmx'

# NodeInfo bean
HDFS_NAME_Node_Info_BEAN = 'Hadoop:service=NameNode,name=NameNodeInfo'

#URL IP and PORT
JMX_ADDRESS = 'http://localhost:50070'
#Check interval
INTERVAL = 30

class HadoopNameNodePlugin(Check):
    def __init__(self):
        self.name = 'hadoop'
        self.frequency = INTERVAL
        Check.__init__(self, self.name)

    def check(self,agentConfig=None):
        startTime = time()

        if agentConfig is None:
            self.log.debug('agentConfig is None,set jmx_address:%s'%JMX_ADDRESS)
            jmx_address = JMX_ADDRESS
        else:
            jmx_address = JMX_ADDRESS

        col_data = self._hdfs_namenode_metrics(jmx_address,HDFS_NAME_Node_Info_BEAN)
        col_data['createdTime']=long(startTime*1000)
        col_data['appName']=self.name
        return col_data

    def _hdfs_namenode_metrics(self,jmx_uri,bean_name):

        response_json = self._rest_request_to_json(jmx_uri,JMX_PATH,query_params={'qry':bean_name})
        response_json = json.loads(response_json)
        node_info = response_json.get('beans',[])

        if node_info:
            node_info = next(iter(node_info))
            for i in ['LiveNodes','DeadNodes']:
                node_num = node_info.get(i,{})
                node_num = json.loads(node_num)
                count = node_num.keys().__len__()
                node_info[i] = count
        return node_info

    def _rest_request_to_json(self,address,object_path,query_params):
        url = address
        if object_path:
            url = self._join_url_dir(address,object_path)

        if query_params:
            query = '&'.join(['{0}={1}'.format(key, value) for key, value in query_params.iteritems()])
            url = urljoin(url, '?' + query)
        self.log.debug('url is:%s' %url)

        req = urllib2.Request(url)
        rep_json = urllib2.urlopen(req).read()
        return rep_json

    def _join_url_dir(self, url, *args):

        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url