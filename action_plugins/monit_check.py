import os
from ansible import utils
from ansible.utils.template import template
from ansible.runner.return_data import ReturnData
from ansible.callbacks import callback_plugins

class ActionModule(object):

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        # note: since this module just calls the template module, the --check mode support
        # can be implemented entirely over there

        VALID_CHECK_TYPES = [ 'process', 'file', 'fifo', 'filesystem', 'directory', 'host', 'system', 'program', 'service']

        # Load up options.
        options  = {}
        if complex_args:
            options.update(complex_args)
        options.update(utils.parse_kv(module_args))

        # Validate the check type is valid and supported.
        check_type = options.get('type', 'service')
        if check_type not in VALID_CHECK_TYPES:
            raise Exception("Unknown check type: '%s'" % check_type)
        if check_type != 'service':
            raise Exception("Check type not supported yet: '%s'" % check_type)

        # Global options.
        name = options.get('name')
        priority = options.get('priority', 20)

        # General options (any type of check).
        inject['name'] = name
        inject['group'] = options.get('group', name)
        if options.has_key('alert'):
            inject['alert'] = options.get('alert')

        if check_type in ('process', 'service'):
            inject['pidfile']       = options.get('pidfile', '/var/run/%s.pid' % name)
            inject['initd']         = options.get('initd', '/etc/init.d/%s' % name)
            inject['start_program'] = options.get('start_program', '%s start' % inject['initd'])
            inject['stop_program']  = options.get('stop_program', '%s stop' % inject['initd'])
            inject['bin']           = options.get('bin', '/usr/sbin/%s' % name)
            inject['service_timeout_restarts']    = options.get('service_timeout_restarts', 5)
            inject['service_timeout_poll_cycles'] = options.get('service_timeout_poll_cycles', 5)
            inject['service_timeout_action']      = options.get('service_timeout_action', 'timeout')

        RESOURCE_TEST_TYPES = {
          'system': ['CPU(user)', 'CPU(system)', 'CPU(wait)', 'SWAP',
                     'MEMORY', 'LOADAVG(1min)', 'LOADAVG(5min)', 'LOADAVG(15min)'
                    ],
          'process': ['CPU', 'TOTAL CPU', 'CHILDREN', 'TOTAL MEMORY',
                     'MEMORY', 'LOADAVG(1min)', 'LOADAVG(5min)', 'LOADAVG(15min)'
                    ],
        }
        RESOURCE_TEST_OPERATORS = [
          "<", ">", "!=", "==",
          "gt", "lt", "eq", "ne",
          "greater", "less", "equal", "notequal",
        ]
        RESOURCE_TEST_ACTIONS = ["ALERT", "RESTART", "START", "STOP", "EXEC", "UNMONITOR"]

        if check_type in ('process', 'system', 'service'):
            resource_tests = options.get('resource_tests', [])
            for test in resource_tests:
                if type(test) is not dict:
                    raise Exception("Resource tests: expected a hash %s" % test)
                required = ('resource', 'operator', 'value', 'action')
                missing = [val for val in test.keys() if val not in required]
                if len(missing) > 0:
                    raise Exception("Resource tests: missing keys in hash %s" % ', '.join(missing))
                if test.resource not in RESOURCE_TEST_TYPES[check_type]:
                    raise Exception("Resource tests: test type %s is not valid for %s check" (test.resource, check_type))
                if test.operator not in RESOURCE_TEST_OPERATORS:
                    raise Exception("Resource tests: invalid operator %s" % test.operator)
                # TODO validate test.value
                if test.action not in RESOURCE_TEST_ACTIONS:
                    raise Exception("Resource tests: invalid action %s" % test.action)
            inject['resource_tests'] = resource_tests

        if check_type in ('file', 'fifo', 'filesystem', 'directory', 'program'):
            inject['path'] = options.get('path')

        # Prepare parameters to run the template.
        # Is there a shortcut to obtain the path to this role/action/module?
        action_path = utils.plugins.action_loader.find_plugin(module_name)
        src = os.path.realpath(os.path.dirname(action_path) + '/../templates/check_%s.j2' % check_type)
        dest = os.path.join(inject['monit_confd_dir'], '%s_check_%s_%s' % (priority, check_type, name))

        module_args = "src=%s dest=%s" % (src, dest)
        handler = utils.plugins.action_loader.get('template', self.runner)
        result = handler.run(conn, tmp, 'template', module_args, inject)

        # Dirty service notification.
        if result.result['changed']:
            cp = callback_plugins[0]
            handler_name = 'restart monit'
            cp.playbook._flag_handler(cp.play, template(cp.play.basedir, handler_name, cp.task.module_vars), inject['inventory_hostname'])

        return result

### Try to run a playbook instead? What about passing in params?
#        action_path = utils.plugins.action_loader.find_plugin(module_name)
#        playbook = os.path.realpath(os.path.dirname(action_path) + '/../tasks/check_%s.yml' % check_type)       
#        Playbook(playbook, ...)

#        result = dict()
#        return ReturnData(conn=conn, comm_ok=True, result=result)

