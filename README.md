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
      roles:
        - sbitmedia.monit
      tasks:
        - action: monit_check type=service name=ntpd
          when: monit_service is defined
```

Notes:

 * It is mandatory to include the role before trying to use monit_check.
 * `monit_service` is a variable defined in the role, so if the variable is
defined, the role is present and running the task makes sense.
 * `action: monit_check` is used instead of the direct form, in order to avoid
syntax errors at compile time if the role is not included. This makes sense when
using `monit_check` from another roles that don't know if sbitmedia.monit is
available.


License
-------

BSD

Author Information
------------------

Jonathan Araña Cruz - SB IT Media, S.L.

