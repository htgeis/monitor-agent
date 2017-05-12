"""Base class for Checks.

If you are writing your own checks you should subclass the AgentCheck class.
The Check class is being deprecated so don't write new checks with it.
"""
# stdlib
from collections import defaultdict
import copy
import logging
import numbers
import os
import re
from time import time
import timeit
import traceback
from types import ListType, TupleType
import unicodedata

# proj
import checks.Metric


class Check(object):
    """
    (Abstract) class for all checks with the ability to:
    * store 1 (and only 1) sample for gauges per metric/tag combination
    * compute rates for counters
    * only log error messages once (instead of each time they occur)

    """
    def __init__(self, checkName=None):
        self.metrics = {}
        if checkName:
            self.log = logging.getLogger('%s.%s' % (__name__, checkName))
        else:
            self.log = logging.getLogger(__name__)
        self._formatter=None

    def normalize(self, metric, prefix=None):
        """Turn a metric into a well-formed metric name
        prefix.b.c
        """
        name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", metric)
        # Eliminate multiple _
        name = re.sub(r"__+", "_", name)
        # Don't start/end with _
        name = re.sub(r"^_", "", name)
        name = re.sub(r"_$", "", name)
        # Drop ._ and _.
        name = re.sub(r"\._", ".", name)
        name = re.sub(r"_\.", ".", name)

        if prefix is not None:
            return prefix + "." + name
        else:
            return name

    def normalize_device_name(self, device_name):
        return device_name.strip().lower().replace(' ', '_')

    def gauge(self, name, value, tags=None, hostname=None, device_name=None, timestamp=None):
        if device_name:
            name = device_name+"."+name
        context = (name,device_name)
        if context not in self.metrics:
            metricNew = Metric.Gauge(self._formatter, name, tags, hostname, device_name)
            self.metrics[context]=metricNew
        self.metrics[context].sample(value)

    def flush(self):
        timestamp = time()
        metrics = []
        for metric in self.metrics:
            metrics += metric.flush(timestamp)

        return metrics

    def combine_and_flush(self,timestamp=None):
        dic = {}
        for context, metric in self.metrics.items():
            me=metric.flushBasic(timestamp)
            dic.update(me[0] if me else {})

        return dic

