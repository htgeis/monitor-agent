# 3p
import yaml  # noqa, let's guess, probably imported somewhere
try:
    from yaml import CLoader as yLoader
    from yaml import CDumper as yDumper
except ImportError:
    # On source install C Extensions might have not been built
    from yaml import Loader as yLoader  # noqa, imported from here elsewhere
    from yaml import Dumper as yDumper  # noqa, imported from here elsewhere

def check_yaml(conf_path):
    with open(conf_path) as f:
        check_config = yaml.load(f.read(), Loader=yLoader)
        assert 'init_config' in check_config, "No 'init_config' section found"
        assert 'instances' in check_config, "No 'instances' section found"

        valid_instances = True
        if check_config['instances'] is None or not isinstance(check_config['instances'], list):
            valid_instances = False
        else:
            for i in check_config['instances']:
                if not isinstance(i, dict):
                    valid_instances = False
                    break
        if not valid_instances:
            raise Exception('You need to have at least one instance defined in the YAML file for this check')
        else:
            return check_config