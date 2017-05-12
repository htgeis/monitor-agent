from time import time

class MetricTypes(object):

    GAUGE = 'gauge'
    COUNTER = 'counter'
    RATE = 'rate'
    COUNT = 'count'

def api_formatter(metric, value, timestamp, tags, hostname=None, device_name=None,
        metric_type=None, interval=None):
    return {
        'metric': metric,
        'points': [(timestamp, value)],
        'tags': tags,
        'host': hostname,
        'device_name': device_name,
        'type': metric_type or MetricTypes.GAUGE,
        'interval':interval,
    }

def basic_formatter(metric, value, timestamp, tags, hostname=None, device_name=None,
        metric_type=None, interval=None):
    return {
        metric:value
    }

class Metric(object):
    """
    A base metric class that accepts points, slices them into time intervals
    and performs roll-ups within those intervals.
    """

    def sample(self, value, sample_rate, timestamp=None):
        """ Add a point to the given metric. """
        raise NotImplementedError()

    def flush(self, timestamp):
        """ Flush all metrics up to the given timestamp. """
        raise NotImplementedError()


class Gauge(Metric):
    """ A metric that tracks a value at particular points in time. """

    def __init__(self, formatter, name, tags, hostname, device_name, extra_config=None):
        self.formatter = formatter or api_formatter
        self.name = name
        self.value = None
        self.tags = tags
        self.hostname = hostname
        self.device_name = device_name
        self.last_sample_time = None
        self.timestamp = time()

    def sample(self, value, sample_rate=None, timestamp=None):
        self.value = value
        self.last_sample_time = time()
        self.timestamp = timestamp


    def flush(self, timestamp):
        if self.value is not None:
            res = [self.formatter(
                metric=self.name,
                timestamp=self.timestamp or timestamp,
                value=self.value,
                tags=self.tags,
                hostname=self.hostname,
                device_name=self.device_name,
                metric_type=MetricTypes.GAUGE,
            )]
            self.value = None
            return res

        return []

    def flushBasic(self, timestamp):
        self.formatter = basic_formatter
        if self.value is not None:
            res = [self.formatter(
                metric=self.name,
                timestamp=self.timestamp or timestamp,
                value=self.value,
                tags=self.tags,
                hostname=self.hostname,
                device_name=self.device_name,
                metric_type=MetricTypes.GAUGE,
            )]
            self.value = None
            return res

        return []