Monit
=====

Install and configure Monit service and allows advanced configuration of checks.

This role provides an action plugin to facilitate configuration of checks. This
is called `monit_check`. See below for details.

This role is Work In Progress. See [`TODO` file](TODO) for some details.

It's fair to say that the whole `monit_check` implementation is quite hacky and
fragile.

 * Ansible doesn't support action plugins in roles. See [this thread](https://groups.google.com/forum/#!msg/ansible-devel/MF4TY-wa9Ww/mL9sVSMd5DwJ) for details.
 * The plugin does its best to notify the restart handler, by hijacking
Ansible's callback_plugins stack.


Requirements
------------

Since ansible doesn't support action plugins in roles, it is needed to
explicitly add the path to this role's action plugins in [`ansible.cfg`](https://github.com/ansible/ansible/blob/devel/examples/ansible.cfg).

Example:

```ini
action_plugins = ./contrib/roles/sbitmedia.monit/action_plugins
```

Happily this path can be relative.

Role Variables
--------------

Look [`defaults/main.yml`](defaults/main.yml) for variables you can override.

See also the params accepted by `monit_check` in [`library/monit_check`](library/monit_check).

Example Usage
-------------

```yaml
    - hosts: servers
      vars:
        monit_check_system_resource_tests:
          - type: 'loadavg(1min)'
            operator: '>'
            value: 24
            tolerance:
              times: 3
              cycles: 5
          - type: 'loadavg(5min)'
            operator: '>'
            value: 12
          - type: 'memory'
            operator: '>'
            value: 75%

        monit_check_filesystems:
          - name: rootfs
            path: /
            tests:
              - type: fsflags
              - type: permission
                value: '0755'
              - type: space
                operator: '>'
                value: 80%

      roles:
        - sbitmedia.monit

      tasks:
        - name: Monit check for ntp service.
          monit_check:
            type: service
            name: ntpd

        - name: Monit check for ssh service.
          action: monit_check type=service name=ssh
          when: monit_service is defined

        - name: Ensure monit system check
          action: monit_check
          args:
            type: system
            tests: "{{ monit_check_system_resource_tests }}"
          when: monit_service is defined

        - name: Ensure monit filesystems check
          action: monit_check
          args:
            type: filesystem
            name: "{{ item.name }}"
            path: "{{ item.path }}"
            tests: "{{ item.tests }}"
          with_items: monit_check_filesystems
          when: monit_service is defined
```

Notes:
 * `monit_check` actions needs the role to be included before. If you're using
`monit_check` inside your own roles, add `sbitmedia.monit` as a role dependency,
or use the second form shown above.
 * `action: monit_check` with `when: monit_service is defined` is useful for a
soft dependency on the role. This makes sense when using `monit_check` in a
role that doesn't know if `sbitmedia.monit` is available.
 * `monit_service` is a variable defined in the role. If the variable is
defined, the role is present, and running the task makes sense.


License
-------

BSD

Author Information
------------------

Jonathan Araña Cruz - SB IT Media, S.L.

