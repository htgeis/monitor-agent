#stdlib
import imp
import traceback
import inspect

#proj
from agentConfig import log

def get_plugin_path(plugin_name):
    return "plugins/"+plugin_name+".py"

def get_plugin_class(plugin_name):
    '''Return the corresponding check class for a check name if available.'''
    from checks import Check
    check_class = None
    plugin_path=get_plugin_path(plugin_name)
    try:
        check_module = imp.load_source('check_%s' % plugin_name, plugin_path)
    except Exception as e:
        traceback_message = traceback.format_exc()
        # There is a configuration file for that check but the module can't be imported
        log.exception('Unable to import check module %s.py from checks.d' % plugin_name)
        return {'error': e, 'traceback': traceback_message}

    # We make sure that there is an AgentCheck class defined
    check_class = None
    classes = inspect.getmembers(check_module, inspect.isclass)
    for _, clsmember in classes:
        if clsmember == Check:
            continue
        if issubclass(clsmember, Check):
            check_class = clsmember
            if Check in clsmember.__bases__:
                continue
            else:
                break
    return check_class

