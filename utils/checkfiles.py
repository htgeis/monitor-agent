"""Helpers to work with check files (Python and YAML)."""
# std
import logging
import os
from urlparse import urljoin

# project
log = logging.getLogger(__name__)


def get_conf_path(check_name):
    """Return the yaml config file path for a given check name or raise an IOError."""
    from agentConfig import get_config_path, PathNotFound
    confd_path = ''

    try:
        confd_path = get_config_path()
    except PathNotFound:
        log.error("Couldn't find the check configuration folder, this shouldn't happen.")
        return None

    conf_path = os.path.join(confd_path, '%s.yaml' % check_name)
    if not os.path.exists(conf_path):
        default_conf_path = os.path.join(confd_path, '%s.yaml.default' % check_name)
        if not os.path.exists(default_conf_path):
            raise IOError("Couldn't find any configuration file for the %s check." % check_name)
        else:
            conf_path = default_conf_path
    return conf_path
