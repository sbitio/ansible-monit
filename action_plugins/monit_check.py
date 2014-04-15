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

        CHECK_TYPES = ['directory', 'fifo', 'file', 'filesystem', 'host', 'process', 'program', 'service', 'system']
        TEST_TYPES = {
          'directory': [],
          'fifo': [],
          'file': [],
          'filesystem': [
              'fsflags', 'space', 'inode', 'perm', 'permission',
          ],
          'host': [],
          'process': [
              'cpu', 'total cpu', 'children', 'total memory',
              'mem', 'memory', 'loadavg(1min)', 'loadavg(5min)', 'loadavg(15min)'
          ],
          'program': [],
          'service': [],
          'system': [
              'cpu(user)', 'cpu(system)', 'cpu(wait)', 'swap',
              'mem', 'memory', 'loadavg(1min)', 'loadavg(5min)', 'loadavg(15min)'
          ],
        }
        TEST_ACTIONS = ['alert', 'restart', 'start', 'stop', 'exec', 'unmonitor']
        TEST_OPERATORS = [
          '<', '>', '!=', '==',
          'gt', 'lt', 'eq', 'ne',
          'greater', 'less', 'equal', 'notequal',
        ]

        # Load up options.
        options  = {}
        if complex_args:
            options.update(complex_args)

        options.update(utils.parse_kv(module_args))

        # Validate the check type is valid and supported.
        check_type = options.get('type', 'service').lower()
        if check_type not in CHECK_TYPES:
            raise Exception("Unknown check type: '%s'" % check_type)
        if check_type not in ('filesystem', 'process', 'service', 'system'):
            raise Exception("Check type not supported yet: '%s'" % check_type)

        # Global options.
        name = options.get('name', None)
        if name is None and check_type == 'system':
            name = inject['inventory_hostname']
        priority = options.get('priority', 20)

        # General options (any type of check).
        inject['name'] = name
        inject['group'] = options.get('group', name)
        if options.has_key('alert'):
            inject['alert'] = options.get('alert')

        #TODO# program?
        if check_type in ('process', 'service'):
            inject['pidfile']       = options.get('pidfile', '/var/run/%s.pid' % name)
            inject['initd']         = options.get('initd', '/etc/init.d/%s' % name)
            inject['start_program'] = options.get('start_program', '%s start' % inject['initd'])
            inject['stop_program']  = options.get('stop_program', '%s stop' % inject['initd'])
            inject['bin']           = options.get('bin', '/usr/sbin/%s' % name)
            inject['service_timeout_restarts']    = options.get('service_timeout_restarts', 5)
            inject['service_timeout_poll_cycles'] = options.get('service_timeout_poll_cycles', 5)
            inject['service_timeout_action']      = options.get('service_timeout_action', 'timeout')

        if check_type in ('directory', 'fifo', 'file', 'filesystem', 'program'):
            inject['path'] = options.get('path')

        # Tests.
        inject['tests'] = []
        for test in options.get('tests', []):
            if type(test) is not dict:
                raise Exception("Tests for %s '%s': expected a hash '%s'" % (check_type, name, test))

            # Test type is valid.
            if test['type'].lower() not in TEST_TYPES[check_type]:
                raise Exception("Tests for %s '%s': invalid test type '%s'" % (check_type, name, test['type']))

            # Test operator is valid.
            if test.has_key('operator') and test['operator'].lower() not in TEST_OPERATORS:
                raise Exception("Tests for %s '%s' (%s): invalid operator '%s'" % (check_type, name, test['type'], test['operator']))

            # Test failure tolerance.
            if test.has_key('tolerance'):
                if (type(test['tolerance']) is not dict or not test['tolerance'].has_key('cycles')):
                    raise Exception("Tests for %s '%s' (%s): tolerance must be a hash. Valid keys: times(optional), cycles." % (check_type, name, test['type']))
                else:
                    if test['tolerance'].has_key('times'):
                        tolerance = 'FOR %(times)s TIMES WITHIN %(cycles)s CYCLES'
                    else:
                        tolerance = 'FOR %(cycles)s CYCLES'
                    test['tolerance'] = tolerance % test['tolerance']

            # Test action.
            if not test.has_key('action'):
                test['action'] = 'alert'
            elif test['action'].lower() not in TEST_ACTIONS:
                raise Exception("Tests for %s '%s' (%s): invalid action '%s'" % (check_type, name, test['type'], test['action']))
            elif test['action'].lower() == 'exec' and not test.has_key('exec'):
                raise Exception("Tests for %s '%s' (%s): missing command for exec action" % (check_type, name, test['type']))

            # Validate mandatory keys for:
            # RESOURCE TESTING: IF resource operator value THEN action
            # SPACE TESTING:    IF SPACE operator value unit THEN action
            # INODE TESTING:    IF INODE operator value [unit] THEN action
            # Note: We don't mind "unit", it must be part of the value.
            if check_type in ('process', 'system', 'service') or test['type'].lower() in ('space', 'inode'):
                if not test.has_key('operator'):
                    raise Exception("Tests for %s '%s' (%s): 'operator' is mandatory" % (check_type, name, test['type']))
                if not test.has_key('value'):
                    raise Exception("Tests for %s '%s' (%s): 'value' is mandatory" % (check_type, name, test['type']))
                condition = '%(type)s %(operator)s %(value)s'

            # FILESYSTEM FLAGS TESTING
            if test['type'] == 'fsflags':
                condition = 'CHANGED %(type)s'

            # PERMISSION TESTING
            if test['type'] in ('perm', 'permission'):
                if not test.has_key('value'):
                    raise Exception("Tests for %s '%s' (%s): 'value' is mandatory" % (check_type, name, test['type']))
                condition = 'FAILED %(type)s %(value)s'

            test['type'] = test['type'].upper()
            if test.has_key('operator'):
                test['operator'] = test['operator'].upper()
            test['condition'] = condition % test
            inject['tests'].append(test)

        # Prepare parameters to run the template.
        # Is there a shortcut to obtain the path to this role/action/module?
        action_path = utils.plugins.action_loader.find_plugin(module_name)
        src = os.path.realpath(os.path.dirname(action_path) + '/../templates/check_%s.j2' % check_type)
        dest = os.path.join(inject['monit_confd_dir'], '%s_check_%s_%s' % (priority, check_type, name))

        module_args = 'src=%s dest=%s' % (src, dest)
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

