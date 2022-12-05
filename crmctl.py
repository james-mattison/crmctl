#!/usr/bin/env python3.6

import argparse
import sys
import os

# Assuming we installed via RPM or by the ./install.sh script, should already be there:

sys.path.insert(0, "/etc/crmctl")
sys.path.append("/etc/crmctl/lib")

# Import the crmctl libs
import lib


help = """
Usage: crmctl <command> [ <subcommand1>, <subcommand2>, ... ]

Commands:

  State Overview:                  crmctl state

  Locate:                          crmctl locate [ master ] <resource>

  Manage:
    Cleanup:                       crmctl clean <resource> [ <node>, all ]
    Ban:                           crmctl ban <resource> [ <node> ]
    Unban:                         crmctl unban <resource> [ <node> ]
    Disable:                       crmctl disable <resource> [ <node> ] 
    Enable:                        crmctl enable <resource> [ <node> ]
    Remote Execute:                crmctl node-exec <node> <command>

  Failover:
    Failover:                      crmctl failover <resource>
    Staggered Restart:             crmctl stagger-restart <resource>
    Transit Masters to Node:       crmctl transit-resources <node>

  Query:
    Cluster Nodes:                 crmctl nodes [ ips ]
    Cluster Resources:             crmctl resources [ <resource> ]
    Cluster Configuration:         crmctl config
    Resource Constraints:          crmctl constraints
    Cluster Properties:            crmctl properties
    EPTT Service Console:          crmctl console <service,mgwd,sipd> <command>
                                   crmctl remote-console <node> <service> <command>

  Server Logs:                     crmctl logs <log_type> [ [ <resource_selector> ], [ <num_lines> ] ]

  Cluster Information Base (CIB):  crmctl tree [ <section> ]
"""


class CommandProcessor:

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.configure_args()
        self.process()

    def configure_args(self):

        self.parser.add_argument(
            "command",
            action="store",
            nargs="*"
        )

    def process(self):
        """ Process a crmctl request."""

        args = self.parser.parse_args()

        def pos(x):
            """
            command structure:
                    popped off -> target
                    VVV
            crmctl command sub third fourth [ *args ]
                            |    |     |
                            0    1     2

            """
            if len(args.command) > x:
                return args.command[x].strip()
            else:
                return ""

        # We got no command; ie `crmctl `
        if len(args.command) == 0:
            failed = "Fatal: No command provided to crmctl. For a list of commands, 'crmctl help'"
            action = ""
        else:
            # We got a command: take this, and turn it into the action to perform, removing it from the 0 position
            # and shifting all commands one position to the left
            action = args.command.pop(0)

        # Subcommand:
        sub = pos(0)

        # Third position, used for optional tertiary commands
        third = pos(1)

        # Fourth position, used for optional quaternary commands
        fourth = pos(2)

        # ... everything _after_ this that gets passed into crmctl is iterated over with pos(x)

        # How many default log lines?
        log_lines = None

        # Load /etc/crmctl/crmctl.conf
        conf_loader = lib.ConfigLoader()
        conf = conf_loader.load_conf()

        if conf:
            log_lines = conf.get("default_maximum_log_lines")
            version = conf.get("version")
            if not version:
                version = 1


        cib = lib.CIBTree()
        crm = lib.CRMResource()
        output_printers = lib.FormattedOutputs()
        console = lib.Console()

        failed = False
        cmd_return = None

        _invalid_args = "Invalid number of args passed; expected either <resource> , or <resource> <node>"

        # - crmctl version
        if action in ["version"]:
            cmd_return = "crmctl: v0.{}".format(version)
            print(cmd_return)

        # - crmctl help
        if action in ["h", "help"]:
            cmd_return = help
            print(cmd_return)

        #  - crmctl clean [ <resource [ <node1>, <node2> ]]
        if action in ["clean", "cn"]:
            if sub == "all":
                cmd_return = crm.cleanup_all()
            elif sub and not third:
                cmd_return = crm.cleanup_resource(sub)
            elif sub:
                for i in range(1, len(args.command)):
                    cmd_return = crm.cleanup_resource_on_node(sub, args.command[i])
            else:
                failed = _invalid_args

        # - crmctl ban <resource> [ <node> ]
        elif action == "ban":
            if sub and third:
                cmd_return = crm.ban_resource_on_node(sub, third)
            elif sub:
                cmd_return = crm.ban_resource(sub)
            else:
                failed = _invalid_args

        # - crmctl unban <resource> [ <node> ]
        elif action == "unban":
            if sub and third:
                cmd_return = crm.unban_resource_on_node(sub, third)
            elif sub:
                cmd_return = crm.unban_resource(sub)
            else:
                failed = _invalid_args

        # - crmctl state
        elif action in ["status", "state", "st"]:
            cmd_return = crm.get_state()

        # - crmctl nodes
        elif action in ["nd", "nodes"]:
            if sub and sub in ["ip", "i", "ips"]:
                cmd_return = crm.list_nodes_and_ips()
            else:
                cmd_return = crm.list_nodes()

        # - crmctl config
        elif action in ["cf", "cnf", "config", "cfg"]:
            cib.get_tree("configuration")
            cmd_return = cib.get_service_configuration()

        # - crmctl properties
        elif action in ["properties", "prop", "pt", "pr"]:
            cmd_return = cib.get_cluster_properties()

        # - crmctl constraints
        elif action in ["constraints", "const", "cnst", "constraint"]:
            cmd_return = output_printers.print_brief_constraints_by_node(sub)

            if sub:
                for frame in cib.get_constraint_attrib_iter():
                    try:
                        for key, value in frame.items():
                            print("{:20s}: {:20s}".format(str(key), str(value)))
                    except:
                        continue

        # - crmctl stagger-restart
        elif action in ["stagger-restart", "stagger", "sf"]:
            if action in ["stagger"] and not sub == "restart":
                cmd_return = "Stagger? restart, reload"
                print(cmd_return)
            else:
                if sub:
                    remaining_args = "/usr/local/eptt/bin/stagger-restart-resource.sh {}".format(sub)
                    cmd_return = lib.LocalExec(remaining_args)
                else:
                    failed = "Invalid command: need target to stagger-restart."

        # - crmctl resources
        elif action in ["r", "rs", "rsc", "resources"]:
            if sub:
                cmd_return = output_printers.print_basic_resource_overview(sub)
            else:
                cmd_return = crm.list_resources()

        # - crmctl tree
        elif action in ["tree", "xt", "xtree"]:
            cmd_return = output_printers.print_cib_tree()

        # - crmctl logs [ <logfilename> ]
        elif action in ["logs", "log"]:
            if sub in ["messages", "docker"]:
                if third and not fourth:
                    fourth = third
                    third = None
                elif third and log_lines:
                    fourth = log_lines

            reader = lib.tools.LogReader(sub, third, num_lines=fourth)
            good_return, logs = reader.readlines()

            if not good_return:
                print(logs)
            else:
                for line in logs:
                    print(line)
            cmd_return = logs

        # - crmctl console
        # - crmctl remote-console
        elif action in ["console", "con", "cns", "remote-console", "rcon", "rcns"]:
            if not third:
                failed = "Fatal: crmctl console <service> [ sum, lic, <console command> ]"
            else:
                if action in ["remote-console", "rcon", "rcns"]:
                    node = sub
                    if not node in crm.list_nodes():
                        failed = "Fatal: crmctl remote-console <node> <service> <command> - did you forget to specify the node?"
                        print(failed)
                        start = 0
                    else:
                        sub = third
                        start = 2
                else:
                    node = None
                    start = 1

                if not failed:
                    remaining_args = []
                    for i in range(start, len(args.command)):
                        remaining_args.append(pos(i))
                    cmd_return = console.console(sub, " ".join(remaining_args), node=node)
                    if not cmd_return.strip().strip("\n"):
                        failed = "No response from console '{}' - is this a valid console target?".format(sub)

        # - crmctl locate <resource>
        # - crmctl locate master <resource>
        elif action in ["loc", "find", "locate"]:
            if sub and sub == "master" and third:
                cmd_return = crm.locate_resource_master(sub)
            elif sub:
                cmd_return = crm.locate_resource(sub)
            else:
                failed = _invalid_args

        # - crmctl failover <resource>
        elif action == "failover":
            if sub:
                if os.path.exists("/usr/local/eptt/bin/monitored-failover.sh"):
                    if sub:
                        cmd_return = lib.LocalExec("/usr/local/eptt/bin/monitored-failover.sh -t {} -m".format(sub))
                    else:
                        print("Do not have monitored-failover.sh!")
                        failed = _invalid_args
                else:
                    failed = help + "Path to monitored-failover does not exist!"
            else:
                failed = "Missing target for monitored failover - cannot continue."

        # - crmctl shift <node>
        elif action in ["transit-resources", "transit-resource", "shift", "fail-to", "failall", "shf", "transit"]:
            if not sub:
                failed = "Fatal: crmctl {} <node>; missing node to fail all master/slave sets too.".format(action)
            elif sub:
                sure = "".join(["WARN: You are about to fail every cluster resource over to {}\n".format(sub),
                                "This may result in multiple failover actions.",
                                "All services will be shifted to node {}. Continue? [N]".format(
                                    sub
                                )])
                yn = input(sure)
                if yn in ["y", "Y", "yes", "Yes"]:
                    cmd_return = lib.LocalExec("/usr/local/eptt/bin/monitored-failover.sh -N {}".format(sub))
            else:
                failed = "Fatal: crmctl {} : cannot fail all resource to node specified - invalid or msisings args."

        # - crmctl node-run <node> <command>
        elif action in ["node-exec", "node-run", "nde", "ndx"]:
            if not sub in crm.list_nodes():
                "Fatal: crmctl node-exec <node> <command> - invalid or unspecified node: {}".format(sub)
            elif not third:
                failed = "Fatal: missing command to execute on node!"
            else:
                to_run = " ".join([args.command[c] for c in range(1, len(args.command))])
                cmd_return = lib.SSHExec(sub, to_run)

        # - Invalid number of args provided, or bad arg combination.
        if failed:
            print(failed)
            print("Fatal: invalid command configuration : {}".format(
                ", ".join([action, ", ".join([c for c in args.command])])
                )
            )

        if not cmd_return:
            print(help)
            passed_in = " ".join(args.command)
            if not action:
                print("Fatal: crmctl requires at least one argument.")
            else:
                print("Fatal: invalid configuration or unknown command given to crmctl: '{}'".format(
                    " ".join([action, passed_in]))
                )


if __name__ == "__main__":
    CommandProcessor()
