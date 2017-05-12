#stdlib
import logging
import logging.handlers
import sys
import traceback
from optparse import OptionParser, Values
import os
import ConfigParser
from cStringIO import StringIO
import string

# proj
from utils.platform import Platform, get_os

# CONSTANTS
AGENT_VERSION = "0.0.1"
AGENT_CONF = "agent.conf"
DEFAULT_CHECK_FREQUENCY=30 #seconds
LOGGING_MAX_BYTES = 10 * 1024 * 1024 #log file size 10M
BASE_LOG_DIR='/var/log/monitor-agent'

class PathNotFound(Exception):
    pass

def get_parsed_args():
    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      dest='verbose',
                      help='Print out stacktraces for errors in checks')
    parser.add_option('-p', '--profile', action='store_true', default=False,
                      dest='profile', help='Enable Developer Mode')

    try:
        options, args = parser.parse_args()
    except SystemExit:
        # Ignore parse errors
        options, args = Values({
                                'verbose': False,
                                'profile': False}), []
    return options, args

def _config_path(directory):
    path = os.path.join(directory, AGENT_CONF)
    if os.path.exists(path):
        return path
    else:
        path = os.path.join(directory, 'conf', AGENT_CONF)
        if os.path.exists(path):
            return path
    raise PathNotFound(path)

def skip_leading_wsp(f):
    "Works on a file, returns a file-like object"
    return StringIO("\n".join(map(string.strip, f.readlines())))

def get_config_path(cfg_path=None, os_name=None):
    # Check if there's an override and if it exists
    if cfg_path is not None and os.path.exists(cfg_path):
        return cfg_path

    # Check if there's a config stored in the current agent directory
    try:
        path = os.path.realpath(__file__)
        path = os.path.dirname(path)
        return _config_path(path)
    except PathNotFound as e:
        pass

    # If all searches fail, exit the agent with an error
    sys.stderr.write("Please supply a configuration file at %s or in the directory where "
                     "the Agent is currently deployed.\n" % path)
    sys.exit(3)


def get_config(parse_args=True, cfg_path=None, options=None):
    if parse_args:
        options, _ = get_parsed_args()

    # General config
    agentConfig = {
        'version': AGENT_VERSION,
        'recv_port':8225,
        'hostname': None,
        'utf8_decoding': False,
        'check_freq': DEFAULT_CHECK_FREQUENCY,
        'run_plugins':[]
    }

    # Find the right config file
    path = os.path.realpath(__file__)
    path = os.path.dirname(path)

    config_path = get_config_path(cfg_path, os_name=get_os())
    config = ConfigParser.ConfigParser()
    config.readfp(skip_leading_wsp(open(config_path)))
    # bulk import
    for option in config.options('Main'):
        agentConfig[option] = config.get('Main', option)

    # Allow an override with the --profile option
    if options is not None and options.profile:
        agentConfig['developer_mode'] = True

    # Core config
    # ap
    if not config.has_option('Main', 'api_key'):
        log.warning(u"No API key was found. Aborting.")
        sys.exit(2)
    if not config.has_option('Main', 'secret_key'):
        log.warning(u"No SECRET key was found. Aborting.")
        sys.exit(2)
    if not config.has_option('Main', 'linklog_url'):
        log.warning(u"No linklog_url was found. Aborting.")
        sys.exit(2)

    if config.has_option('Main', 'check_freq'):
        try:
            agentConfig['check_freq'] = int(config.get('Main', 'check_freq'))
        except Exception:
            pass
    if config.has_option('Main', 'run_plugins'):
        try:
            agentConfig['run_plugins'] = config.get('Main', 'run_plugins').split(',')
        except Exception:
            pass

    return agentConfig


def _get_logging_config(cfg_path=None):
    levels = {
        'CRITICAL': logging.CRITICAL,
        'DEBUG': logging.DEBUG,
        'ERROR': logging.ERROR,
        'FATAL': logging.FATAL,
        'INFO': logging.INFO,
        'WARN': logging.WARN,
        'WARNING': logging.WARNING,
    }

    config_path = get_config_path(cfg_path, os_name=get_os())
    config = ConfigParser.ConfigParser()
    config.readfp(skip_leading_wsp(open(config_path)))

    logging_config = {
        'log_level': logging.INFO,
    }
    if config.has_option('Main', 'log_level'):
        logging_config['log_level'] = levels.get(config.get('Main', 'log_level'))
    if config.has_option('Main', 'disable_file_logging'):
        logging_config['disable_file_logging'] = config.get('Main', 'disable_file_logging').strip().lower() in ['yes', 'true', 1]
    else:
        logging_config['disable_file_logging'] = False

    system_os = get_os()
    global BASE_LOG_DIR
    if system_os != 'windows' and not logging_config['disable_file_logging']:
        if not os.access(BASE_LOG_DIR, os.R_OK | os.W_OK):
            print("{0} dir is not writeable, so change it to local".format(BASE_LOG_DIR))
            BASE_LOG_DIR = "logs"
        logging_config['collector_log_file'] = '{0}/collector.log'.format(BASE_LOG_DIR)
        logging_config['forwarder_log_file'] = '{0}/forwarder.log'.format(BASE_LOG_DIR)
        logging_config['{0}_log_file'.format(__name__)] = '{0}/monitor.log'.format(BASE_LOG_DIR)

    return logging_config

def _get_log_date_format():
    return "%Y-%m-%d %H:%M:%S %Z"

def _get_log_format(logger_name=None):
    if get_os() != 'windows' and logger_name:
        return '%%(asctime)s | %%(levelname)s | dd.%s | %%(name)s(%%(filename)s:%%(lineno)s) | %%(message)s' % logger_name
    return '%(asctime)s | %(levelname)s | %(name)s(%(filename)s:%(lineno)s) | %(message)s'

def initialize_logging(logger_name):
    logging_config=_get_logging_config()

    try:
        logging.basicConfig(
            level=logging_config['log_level'] or logging.INFO,
            format=_get_log_format()
        )

    except Exception as e:
        sys.stderr.write("Couldn't initialize logging: %s\n" % str(e))
        traceback.print_exc()

    log_file = logging_config.get('%s_log_file' % logger_name)
    if log_file is not None and not logging_config['disable_file_logging']:
        # make sure the log directory is writeable
        # NOTE: the entire directory needs to be writable so that rotation works
        if os.access(os.path.dirname(log_file), os.R_OK | os.W_OK):
            file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=LOGGING_MAX_BYTES, backupCount=1)
            formatter = logging.Formatter(_get_log_format(logger_name), _get_log_date_format())
            file_handler.setFormatter(formatter)

            root_log = logging.getLogger()
            root_log.addHandler(file_handler)
        else:
            sys.stderr.write("Log file is unwritable: '%s'\n" % log_file)

    # re-get the log after logging is initialized
    global log
    log = logging.getLogger(__name__)

log=logging.getLogger(__name__)