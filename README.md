Monit
=====

Performs installation and configuration of Monit service.

Provides an action plugin to facilitate configuration of checks. See below for
details.

This role is Work In Progress. See [`TODO` file](TODO.md) for some details.

It's fair to say that the whole action plugin implementation is quite hacky and
fragile.

 * Ansible doesn't support action plugins in roles. See [this thread](https://groups.google.com/forum/#!msg/ansible-devel/MF4TY-wa9Ww/mL9sVSMd5DwJ)
for details.
 * The plugin does its best to notify the restart handler, by hijacking
Ansible's callback_plugins stack.


Requirements
------------

Since Ansible doesn't support action plugins in roles, it is needed to
explicitly add the path to this role's action plugins in [`ansible.cfg`](https://github.com/ansible/ansible/blob/devel/examples/ansible.cfg).

Example:

```ini
action_plugins = ./contrib/roles/sbitmedia.monit/action_plugins
```

Happily, action_plugins supports relative paths. Paths are separated by colon
(`:`).


Role Variables
--------------

The role provides sane defaults, and respects configuration files provided by
the OS whenever possible.

Default variables are documented in [`defaults/main.yml`](defaults/main.yml).

Role variables are set per OS. See: [`vars/*.yml`](vars/).

See also the args accepted by `monit_check` in [`library/monit_check`](library/monit_check).


Example Usage
-------------

Using the role is straightforward, just include it and set overrides as needed.

Following playbook shows several examples of `monit_check` usage. In a bird-eye
view it does the folliwing:

 * Declare two variables with configuration data for several checks.
 * includes the role.
 * performs four tasks showing different ways to use `monit_check`.

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

 * `monit_check` actions needs the role to be included before. If want to use
`monit_check` inside your own roles, read below section Leverage monit role.
 * `action: monit_check` with `when: monit_service is defined` is useful for a
soft dependency on the role. This makes sense when using `monit_check` in a
role that doesn't know if `sbitmedia.monit` is available.
 * `monit_service` is a variable defined in the role. If the variable is
defined, the role is present, and running the task makes sense.


Leverage monit in your roles
----------------------------

Sumarizing above notes. There's two ways to leverage this role in your own roles.

 * Hard dependency: add `sbitmedia.monit` as a dependency in your role and start
ruling your own checks with no drawbacks at all.

 * Soft dependency: use `sbitmedia.monit` when it is available. For this to
work, several thing need to happen:
1. the role must be included before yours.
1. calls to `monit_check` must be done this way, to avoid syntax errors in
Ansible:

```yaml
- name: Ensure monit system check
  action: monit_check
  args:
    type: system
    tests: "{{ monit_check_system_resource_tests }}"
  when: monit_service is defined
```

You can see a full-fledged pattern for integration of external services in
[sbitmedia.fail2ban](https://github.com/sbitmedia/ansible-fail2ban). See its
[`main.yml`](https://github.com/sbitmedia/ansible-fail2ban/blob/master/tasks/main.yml#L34)
along with [`external.yml`](https://github.com/sbitmedia/ansible-fail2ban/blob/master/tasks/external.yml)
and [`external/*`](https://github.com/sbitmedia/ansible-fail2ban/blob/master/tasks/external).

License
-------

BSD

Author Information
------------------

Jonathan Araña Cruz - SB IT Media, S.L.

