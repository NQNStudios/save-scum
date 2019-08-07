import commentjson
import os.path
import inspect
from savescum import logs

def json():
    ''' Return a JSON config object from ~/.save-scum.json,
    falling back on the example configuration (which, hey, just
    might work!)
    '''
    config_file = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/../example-config.json'
    custom_config_file = os.path.expanduser('~/.save-scum.json')
    if os.path.exists(custom_config_file):
        config_file = custom_config_file

    with open(config_file) as f:
        return commentjson.load(f)
    
def log_functions():
    ''' Return a list of functions f(s) that print log messages.
    By default, includes print(), but can also send email and Discord
    messages with proper JSON config.
    '''
    functions = [ print ]

    config = {}
    if 'logging' in json():
        config = json()['logging']

    if 'discord-webhook' in config and len(config['discord-webhook']) > 0:
        functions.append(logs.discord)

    if 'downmail' in config and len(config['downmail']) > 0:
        try:
            import downmail
            functions.append(logs.downmail)
        except Error as e:
            for function in functions:
                function('Downmail is not installed!')
    return functions
    
    
