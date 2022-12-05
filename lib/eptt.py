import socket
import subprocess
import os
from .crm import CRMResource


class Console:
    """
    Inject a command into an EPTT service's debug console. Currently supports epttd, mgwd, rabbitmq
    """

    permitted_consoles = {
        "mgwd": 7000,
        "rabbitmq": 5672
    }

    cmd = None
    port = 20000
    console_target = None
    node_target = None

    def __init__(self):
        pass

    @classmethod
    def _process_console_target(cls):
        if cls.console_target == "mgwd":
            cls.console_target = "172.17.1.2"
            cls.port = cls.permitted_consoles["mgwd"]
        elif cls.console_target == "rabbitmq":
            cls.console_target = "0.0.0.0"
            cls.port = cls.permitted_consoles["rabbitmq"]

    @classmethod
    def _local_console(cls) -> str:
        """
        Pipe a command into a debug console running locally, and return its results as a string.
        """
        _r = []

        cls._process_console_target()
        for command in cls.cmd:
            console_pipe = 'echo -e "\r\n\r\n{} \r\n" | nc {} {}'.format(command, cls.console_target, cls.port)
            #        print(console_pipe)
            _r.append(subprocess.run(
                console_pipe, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            )

            returns = "\n".join([x.stdout.decode(errors='ignore') for x in _r])
            print(returns)
            return returns

    @classmethod
    def _remote_console(cls) -> str:
        """
        Pipe a command into the debug console on a remote machine, and retrun its results as a string.
        """
        _r = []
        cls._process_console_target()
        command = " ".join(cls.cmd)
        remote_console_command = """ssh {} 'echo -e "\\r\\n\\r\\n{} \\r\\n" | nc {} {}'""".format(cls.node_target,
                                                                                                  command,
                                                                                                  cls.console_target,
                                                                                                  cls.port)
        print(remote_console_command)
        crun = subprocess.run(remote_console_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = crun.stdout.decode(errors='ignore')
        if "address associated" in out:
            print("crmctl remote-console <node name> <service name> <command>")
            print("Fatal: bad service name provided: {}. No reply from console.".format(cls.console_target))
        else:
            print(out)
        return out

    @classmethod
    def console(cls, console_target: str, *cmd, node: str = None) -> str:
        """ Pipe a command directly into the """
        cls.console_target = console_target
        cls.cmd = cmd
        cls.node_target = node

        if cls.console_target in cls.permitted_consoles.keys():
            cls.port = cls.permitted_consoles.get(cls.node_target)
        else:
            cls.port = 20000

        if cls.node_target:
            return cls._remote_console()
        else:
            return cls._local_console()
