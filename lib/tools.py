import subprocess
import os


class ConfigLoader:
    """ Load /etc/crmctl.crmctl.conf"""

    cnf = {}

    def load_conf(self, config_file="/etc/crmctl/crmctl.conf"):
        try:
            with open(config_file, "r") as _o:
                raw_config = _o.readlines()
            for line in raw_config:
                if "=" in line:
                    config_key, config_value = line.split("=")
                    config_key = config_key.strip()
                    config_value = config_value.strip()
                    try:
                        config_value = bool(config_value)
                    finally:
                        self.cnf[config_key] = config_value
                    self.cnf[config_key] = config_value
            return self.cnf
        except FileNotFoundError:
            print("UNABLE TO LOAD CONFIG.")
            return {}

    def get_config(self):
        return self.cnf


class LogReader:
    """ crmctl logs <resource_type> <identifier>

    if <resource_type> is 'messages' or 'docker', identifier is not required.

    usage:
        crmctl logs epttd ewave01 25
            ... return 25 logs of /var/log/epttd/EPTT_ewave01.log

        crmctl logs epttd ewave01
            ... print the default number of lines (if in crmctl.conf, else 250) of
                /var/log/epttd/EPTT_ewave01.log

        crmctl logs messages
            ... return configured max lines, default 250, of messages
    """

    paths = {
        "epttd": "/var/log/epttd",
        "pushd": "/var/log/pushd/pushd.log",
        "leeotard": "/var/log/leeotard/leeotard.log",
        "mgwd": "/var/log/mgwd/mgwd-0.log",
        "portal": "/var/log/web",
        "sales": "/var/log/web/EPTT_sales.log",
        "rabbitmq": "/var/log/rabbitmq",
        "sipd": "/var/log/sipd/sipd.log",
        "messages": "/var/log/messages",
        "docker": "/var/log/docker"
    }

    def __init__(self, log_type: str, log_specifier: str = None, num_lines: int = None) -> None:
        self.log_type = log_type
        self.log_specifier = log_specifier
        self.log_num_lines = int(num_lines) if num_lines else None

        _s = "Read: Log -> {} (source: {})".format(self.log_specifier if self.log_specifier else "", self.log_type)
        if self.log_num_lines:
            _s += " [ # lines {} ]".format(self.log_num_lines)

        print(_s)

    def _parse_selectors(self) -> (bool, str):
        """ parse everything after crmctl logs. Returns a tuple: (True, log path), or (False, failure message)."""

        def validate(path):
            if not os.path.exists(path):
                print("Fatal: invalid log path requested -> {}".format(path))
                return False
            else:
                return True

        if not self.log_type in self.paths.keys():
            return (False, "Fatal: invalid log type {} -  must select from: \n{}".format(
                self.log_type, "\n".join(list(self.paths.keys()))
            )
                    )

        # -- /var/log/messages
        if self.log_type in ["msg", "msgs", "ms", "mg", "messages"]:
            if validate(self.paths["messages"]):
                return True, self.paths["messages"]

        # -- /var/log/docker
        elif self.log_type in ["docker", "dock", "dk"]:
            if validate(self.paths["docker"]):
                return True, self.paths["docker"]

        # -- /var/log/sipd/sipd.log
        elif self.log_type in ["sipd", "sip"]:
            if validate(self.paths["sipd"]):
                return True, self.paths["sipd"]

        # -- /var/log/pushd/pushd.log
        elif self.log_type in ["pushd"]:
            if validate(self.paths["pushd"]):
                return True, self.paths["pushd"]

        # -- /var/log/leeotard/leeotard.log
        elif self.log_type in ["otar", "leeotard"]:
            if validate(self.paths["leeotard"]):
                return True, self.paths["leeotard"]

        # -- /var/log/epttd/<selector>
        elif self.log_type == ["eptt", "ptt", "epttd"]:
            if not self.log_specifier:
                return False, "Fatal: missing service name in crmctl logs epttd <service name>"

            if not validate(self.paths["epttd"] + "/" + self.log_specifier):
                return False, "Fatal: unable to parse epttd logs: the requested service {} does not exist.\n".format(
                    self.log_specifier)
            else:
                target = self.paths["epttd"] + "/" + self.log_specifier + "/EPTT_" + self.log_specifier + ".log"
                if not validate(target):
                    return False, "Fatal: bad service target for log viewing: {} does not exist.".format(
                        self.log_specifier)
                else:
                    return True, target

        # -- /var/log/web/EPTT_sales.log
        elif self.log_type in ["sales"]:
            if validate(self.paths["sales"]):
                return True, self.paths["sales"]
            else:
                return False, "{} does not exist - wrong node?".format(self.paths["sales"])

        # -- /var/log/web/EPTT_<selector>.log
        elif self.log_type in ["web", "webservices"]:
            ws = self.paths["webservices"] + "/EPTT_" + self.log_specifier + ".log"
            if not validate(ws):
                return False, "Fatal: Unable to return webservices log for service {} - bad node or service name?".format(
                    ws
                )
            else:
                return True, ws

        else:
            return False, "Fatal: invalid type returned; cannot select logs from {} / {}".format(
                self.log_type, self.log_specifier)

    def _select_log_lines(self) -> (bool, list):
        """ Get the required number of lines from the requested log file. If this file is not valid or
        has no contents, then return (False, []), else (True, lines)"""
        good_return, log_filename = self._parse_selectors()

        #  bad file given, other problem - we did not get the log lines we wanted.
        if not good_return:
            return good_return, log_filename

        # If the user passes in say crmctl logs messages 25, return only 25 lines.
        if self.log_num_lines:
            limit = self.log_num_lines
        else:
            limit = 200

        # Cheat and tail the logs. Todo: implement ssh log-getting too.

        blob = subprocess.getoutput("tail -n {} {}".format(limit, log_filename))

        lines = [line for line in blob.split("\n")]

        return True if lines else False, lines

    def readlines(self, limit=None) -> (bool, list):
        """ Read either 200, or 'limit', lines from the selected log. Return (True, lines) if OK, else (False, Error)"""
        if limit:
            self.log_num_lines = limit
        good_ret, lines = self._select_log_lines()
        return good_ret, lines

    def read(self, limit=None):
        read_return, lines = self.readlines(limit=limit)
        return read_return, "\n".join(lines)

    def get_log_paths(self, **kwargs):
        if kwargs.get("keys_only"):
            return self.paths.keys()
        elif kwargs.get("values_only"):
            return self.paths.values()
        else:
            return self.paths

    def get_iterator(self, limit=None):
        _, lines = self.readlines(limit=limit)
        for line in lines:
            yield line

    def get_log_path_iter(self):
        for key, value in self.paths.items():
            yield (key, value)


class _LocalExec:
    """ Helper: execute a command locally."""

    def __call__(self, cmd):
        self.cmd = cmd
        return self._lrm_exec()

    def _lrm_exec(self) -> str:
        c = []
        local_command_exec = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        while local_command_exec.poll() == None:
            ln = local_command_exec.stdout.readline().decode(errors='ignore')
            if ln:
                print(ln.strip("\n"))
                c.append(ln)
        return "".join(c)


class _SSHExec:
    """ Helper: execute a command over SSH. """

    def _get_cmd(self, target, cmd):
        return "ssh {} '{}'".format(target, cmd)

    def __call__(self, target, cmd):
        self.cmd = self._get_cmd(target, cmd)
        exec_agent_output = LocalExec(self.cmd)
        return exec_agent_output


SSHExec = _SSHExec()
LocalExec = _LocalExec()
