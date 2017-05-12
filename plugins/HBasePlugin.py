import json
import logging
import urllib2
from time import time
from urlparse import urljoin

from checks import Check

# URL Paths
JMX_PATH = 'jmx'

# NodeInfo bean
HBASE_INFO_BEAN = 'hadoop:service=Master,name=Master'

#URL IP and PORT
JMX_ADDRESS = 'http://localhost:60010'

#Check interval
INTERVAL = 30

class HBasePlugin(Check):
    def __init__(self):
        self.name = 'hbase'
        self.frequency = INTERVAL

        Check.__init__(self,self.name)

    def check(self,agentConfig=None):
        startTime = time()

        if agentConfig is not None:
            jmx_address = agentConfig.get("JMX_ADDRESS",JMX_ADDRESS)
        else:
            jmx_address = JMX_ADDRESS

        col_data = self._hbase_metrics(jmx_address,HBASE_INFO_BEAN)
        col_data['createdTime']=long(startTime*1000)
        col_data['appName']=self.name
        return col_data

    def _hbase_metrics(self,jmx_uri,bean_name):

        response_json = self._rest_request_to_json(jmx_uri,JMX_PATH,query_params={'qry':bean_name})
        response_json = json.loads(response_json)
        beans = response_json.get('beans',[])

        col_content = {}
        region_name = []
        if beans:
            master_content = next(iter(beans))
            for k,v in master_content.items():
                if k=='AverageLoad':
                    col_content[k] = v
                if k=='RegionServers':
                    region_name = []
                    col_content['server_live_nums'] = len(v)
                    for index in range(len(v)):
                        region_name.append(v[index].get('key'))
                    col_content['server_live_name'] = region_name
                if k=='DeadRegionServers':
                    region_name = []
                    col_content['server_dead_nums'] = len(v)
                    region_name = v
                    col_content['server_dead_name'] = region_name
        return col_content

    def _rest_request_to_json(self,address,object_path,query_params):
        url = address
        if object_path:
            url = self._join_url_dir(address,object_path)

        if query_params:
            query = '&'.join(['{0}={1}'.format(key, value) for key, value in query_params.iteritems()])
            url = urljoin(url, '?' + query)

        req = urllib2.Request(url)
        rep_json = urllib2.urlopen(req).read()
        return rep_json

    def _join_url_dir(self, url, *args):

        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url