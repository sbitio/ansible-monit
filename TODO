- Support EVERY: https://mmonit.com/monit/documentation/monit.html#service_poll_time

- Support SUCCEEDED predicate: IF <TEST> THEN <ACTION> [ELSE IF SUCCEEDED THEN ACTION]

- Support EXISTENCE TESTING
- Support FILE CHECKSUM TESTING
- Support TIMESTAMP TESTING
- Support FILE SIZE TESTING
- Support FILE CONTENT TESTING
- Support UID TESTING
- Support GID TESTING
- Support PID TESTING
- Support PPID TESTING
- Support PROCESS UPTIME TESTING
- Support PROGRAM STATUS TESTING
- Support PING TESTING
- Support CONNECTION TESTING

Document a pattern to allow roles leveraging this one to skip monit. Implement
the pattern in sbitmedia.fail2ban, etc. Example:

```yaml
when: monit_service is defined and fail2ban_monit_skip is not defined
```

