import subprocess
import os
import sys

from . import *
from .tools import LocalExec

"""
crm.py: Helpers that use the crm_resource (and crm_node) to interact with the cluster at a higher
level than the CIB.
"""


class ClusterResourceManager(object):
    """ Manage the CRM. """
    pass


class CRMResource(ClusterResourceManager):

    # def __init__(self):
    #     self.exec_agent = LocalExec
    #
    @classmethod
    def locate_resource(cls, resource: str) -> str:
        """ Get the node names that the resource is running on. """
        return LocalExec("crm_resource --locate --resource {}".format(resource))

    @classmethod
    def locate_resource_master(cls, resource: str) -> str:
        """ Get the node name that the master for a master/slave set is running on."""
        return LocalExec("crm_resource --locate --resource {} --master".format(resource))

    @classmethod
    def ban_resource_on_node(cls, resource: str, node: str) -> str:
        """ Ban the resource on specified node."""
        return LocalExec("crm_resource --resource {} --ban --node {}".format(resource, node))

    @classmethod
    def ban_resource(cls, resource: str) -> str:
        return LocalExec("crm_resource --resource {} --ban".format(resource))

    @classmethod
    def unban_resource_on_node(cls, resource: str, node: str) -> str:
        return LocalExec("crm_resource --resource {} --clear --node {}".format(resource, node))

    @classmethod
    def unban_resource(cls, resource: str) -> str:
        return LocalExec("crm_resource --resource {} --clear".format(resource))

    @classmethod
    def cleanup_resource_on_node(cls, resource: str, node: str) -> str:
        return LocalExec("crm_resource --resource {} --cleanup --node {} --force --quiet".format(resource, node))

    @classmethod
    def cleanup_resource(cls, resource: str) -> str:
        return LocalExec("crm_resource --resource {} --cleanup --quiet".format(resource))

    @classmethod
    def cleanup_all(cls) -> str:
        return LocalExec("crm_resource --cleanup --force --quiet")

    @classmethod
    def list_resources(cls) -> str:
        return LocalExec("crm_resource --list-raw | cut -d ':' -f 1 | sort -u")

    @classmethod
    def list_nodes(cls) -> str:
        return LocalExec("crm_node --list")

    @classmethod
    def list_nodes_and_ips(cls):
        return LocalExec(
            "cat /etc/hosts | grep -v localhost | grep -v '::' | grep -v 172 | cut -d ' ' -f 1,2 | grep -E 'ptt.*|priv.*|web'")

    @classmethod
    def get_state(cls) -> str:
        return LocalExec("crm_mon --one-shot --show-detail")

    @classmethod
    def get_resource_names(cls, exclude_failed=False) -> dict or list:
        """
        Retrieve a list of resource names. If exclude_failed, only return resources that are
        in a good/running state.
        """
        raw_resources = LocalExec("crm_resource --list-raw | cut -d ':' -f 1 | sort -u")
        resources = [res.strip() for res in raw_resources.split("\n")]
        failed = cls.get_failed_resources()
        if exclude_failed:
            for i, f in enumerate(failed):
                for r in resources:
                    if f.get("resource") in r:
                        resources.remove(r)
        return resources

    @classmethod
    def get_ptt_resource_names(cls) -> list:
        """ Return a list of epttd/epttd-docker resources, with -master stripped off."""
        ptt_names = []
        for r in cls.get_resource_names(exclude_failed=False):
            if "EPTT_" in r:
                if "-master" in r:
                    r = r.strip("\-master")
                ptt_names.append(r)
        return ptt_names

    @classmethod
    def get_failed_resource_names(cls, append_location=True, with_button_type=False) -> list:
        """ Retrieve a list of all resources in a failed state."""
        names = []
        for o in cls.get_failed_resources():
            if not with_button_type:
                if not o.get("resource") in names:
                    if append_location:
                        names.append(o.get("resource") + "-" + o.get("node"))
                    else:
                        names.append(o.get("resource"))
            else:
                names.append(o)
        return names

    @classmethod
    def get_resource_locations(cls) -> dict:
        """ Retrieve a mapping of { RESOURCE: RUNNING_ON } for each resource in the cluster."""
        rscs = {}
        for resource in cls.get_resource_names():
            loc = LocalExec("crm_resource --resource {} --locate --quiet".format(resource)).split("\n")
            rscs[resource] = loc
        return rscs

    @classmethod
    def get_resource_types(self, as_dict=True) -> dict or list:
        """
        Retrieve a list the type of each resource in this cluster.
        If as_dict, then a mapping like { resource_name: resource_type, .. } is returned.
        """
        resource_types = LocalExec(
            "crm_resource --list | grep -E 'Clone.*|Master\/Slave.*|\:\:sla.*' | xargs -l | awk '{ print $1, $2, $NF }' | tr '[' ' ' | tr ']' ' '")
        if not as_dict:
            return [s.strip() for s in resource_types.split("\n")]
        else:
            ret_map = {}
            for resource_t in resource_types.split("\n"):
                if not "Set:" in resource_t:
                    r = resource_t.split(")")[1].strip()
                    v = "Primitive"
                else:
                    r = resource_t.split("Set:")[1].strip()
                    v = resource_t.split("Set:")[0].lstrip().strip()
                ret_map[r] = v
            return ret_map

    @classmethod
    def get_failed_resources(cls) -> list:
        """
        Get all failed resources, as a list of dictionaries with keys 'resource', 'node', 'button'
        """
        failed = []

        raw_failed = LocalExec(
            "crm_mon -1 | grep -E 'FAILED.*|Stopped' | sed 's/[(].*[):]//g' | awk '{ print $1, $3 }'")
        failed_on_nodes = raw_failed.split("\n")

        for resource_failure in failed_on_nodes:
            try:
                resource, node = resource_failure.split(" ")
                f = {
                    "resource": resource,
                    "node": node,
                    "button": "danger"
                }
                failed.append(f)
            except ValueError:
                print("No failed resources found")
        return failed

    @classmethod
    def get_locations(cls, resource) -> list:
        """ Retrive a list of pcs short names of the locations where this resource is running."""
        where = LocalExec(
            "crm_resource --resource {} --locate --quiet | xargs".format(resource)).strip("\n").split()
        return where

