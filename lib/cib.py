from xml.etree import ElementTree
import subprocess
from typing import Iterable


class Tree(object):
    """
    Parsers for the XML Tree object which forms the Cluster Information base: the cluster's running configuration.
    """

    tree: ElementTree = None
    managed_objects = []
    permitted_scopes = ["nodes", "resources", "constraints", "crm_config", "rsc_defaults", "op_defaults", "status"]

    def __init__(self, selector: str = None):
        self.tree = self.__call__(selector=selector)

    def __call__(self, *args, **kwargs) -> ElementTree:
        tree = self.get_tree(selector=kwargs.get("selector"))
        self.managed_objects = [i for i in tree.iter()]
        return tree

    @classmethod
    def get_tree(cls, selector=None) -> ElementTree:
        """ Returns an xml.etree.ElementTree object containing the whole of the CIB"""
        if selector:
            tree = ElementTree.fromstring(subprocess.getoutput("cibadmin --query --scope {}".format(selector)))
        else:
            tree = ElementTree.fromstring(subprocess.getoutput("cibadmin --query"))
        cls.tree = tree
        return tree

    @classmethod
    def get_iter(cls) -> Iterable:
        """
        Return an iterable of the entire tree.
        """
        return cls.tree.iter()

    @classmethod
    def get_num_managed(cls) -> int:
        """ Return an integer of the total number of tags in the entire CIBTree XML ElementTree object."""
        tree = cls.get_tree()
        return len([i for i in tree.getiterator()])


class CIBTree(Tree):
    """
    Traverse and parse the CIB's ElementTree.
    """

    def pull_section(self, section_key: str) -> ElementTree:
        """ Return every single tag in the section 'section_key' as a list """
        return self.get_tree(section_key)

    def get_object_types(self) -> list:
        """ Return a list of object types found in the CIB. """
        types = []
        for ob in self.get_iter():
            if not ob.tag in types:
                types.append(ob.tag)
        return types

    def get_object_ids(self) -> list:
        """ return a list of raw identifiers for each object"""
        return [ob.get("id") for ob in self.get_iter()]

    def get_resource_attrib_iter(self) -> Iterable[dict]:
        """ Returns a generator of each resource's configuration XML tags. """
        resources = self.pull_section("resources")
        for resource in resources.iter():
            if resource.attrib:
                yield resource.attrib

    def get_constraint_attrib_iter(self) -> Iterable[dict]:
        """ Return a generator of all the constraints on all resources in the CIB. """
        constraints = self.pull_section("constraints")
        for constraint in constraints.iter():
            if constraint.attrib:
                yield constraint.attrib

    def get_node_attrib_iter(self) -> Iterable[dict]:
        """ Return an iterator of all properties directly relating to the nodes defined in cluster.conf, including
        their state. """
        nodes = self.pull_section("nodes")
        for node in nodes.iter():
            if node.attrib:
                yield node.attrib

    def get_cib_config(self) -> ElementTree:
        """ This returns the closest one can get to a straight through A-Z list iterable of all the XML tags that
        are registered in the CIB. """
        cib = CIBTree.get_tree("configuration")
        for frame in cib.iter():
            if frame.tag == "cib":
                cib = frame.attrib
                break
        if not cib:
            raise Exception("Fatal: unable to parse the cib!")
        else:
            return cib

    def get_cib_resources(self) -> list:
        """ Recursively flatten each resource in the CIB's 'resources' tag, and return it as a list of dicts"""
        resource_blobs = []
        for resource in self.get_resource_attrib_iter():
            resource_blobs.append(resource)
        return resource_blobs

    def get_cib_resource_constraints(self, resource_name) -> dict:
        """ Return a dict of the resource's constraints, with keys:
        enabled_on, disabled_on, resource, type. """

        resource_constraints = {
            "enabled_on": [],
            "disabled_on": [],
            "type": None,
            "resource": None
        }

        for constraint in self.pull_section("constraints"):
            # Be selective by resource - we only want the ones that have the resource name in the id:
            if not resource_name in constraint.get("id"):
                continue

            # Give the name that the resource will use for indexing
            resource_constraints["resource"] = constraint.get("rsc")

            # Traverse the constraints section of the CIB:
            for topkey, topval in constraint.items():
                # Extract constraint type from location-EPTT_test1-master-priv2--INFINITY
                resource_constraints["type"] = constraint.get("id").split("-")[0]

                # parse if it is a prefers constraint or an avoids constraint
                if topkey == "score":
                    # avoid (neg affinity)
                    if topval == "-INFINITY":
                        nd = constraint.get("node")
                        if not nd in resource_constraints["disabled_on"]:
                            resource_constraints["disabled_on"].append(constraint.get("node"))
                    # prefer (pos affinity)
                    elif topval == "INFINITY":
                        nd = constraint.get("node")
                        if not nd in resource_constraints["enabled_on"]:
                            resource_constraints["enabled_on"].append(constraint.get("node"))
                    # if this is a custom constraint with an integer value, don't bother.
                    else:
                        print("Strange: invalid constraint for node {}".format(constraint.get("node")))

        # Return the constraints.
        return resource_constraints

    def get_service_configuration(self):
        """
        Get the configuration of all resources in the CRM; returns a list of dictionaries, with k:v in order.
        Equivalent to the config section of pcs config --full
        """
        config = []
        o = {}
        xkey = ""
        for resource in self.get_resource_attrib_iter():
            if resource.get("class"):
                print("\n--------- {} ---------".format(resource.get("type")))
                o = {}
                o["name"] = resource.get("type")
            for k, v in resource.items():
                if k == "name":
                    if v in ["op", "id", "stop", "start", "promote", "demote", "monitor", "OCF_CHECK_LEVEL"]:
                        continue
                    print("{:20s} : ".format(v), end="", flush=True)
                    xkey = v
                if k == "value":
                    if xkey:
                        print("{:20s}".format(v))
                        o[xkey] = v
                        xkey = ""
            if o:
                config.append(o)
        return config

    def get_cluster_properties(self):
        """ Retrieve cluster properties in a dict; replaces pcs property --full."""
        property_tree = self.get_tree("crm_config")
        properties = {}
        print("------- Cluster Properties --------")
        for property in property_tree.iter():
            key = property.get("name")
            value = property.get("value")
            if key:
                properties[key] = value
                print("{:35s}: {:25s}".format(str(key), str(value)))
        return properties

    def recurse_tree(self) -> list:
        """
        Trace each element of the tree down to its lowest child level, flattening the tree.
        Removes the section tags; the output is a list of each XML section as though it were a
        single array, in a dict. I wanna punch the guy who invented XML in the face.
        """

        def recurse_down(xtree_object):
            if not xtree_object.getchildren():
                return False
            else:
                return xtree_object.getchildren()

        # This will be the list of the tag:{ **attrib } pairings
        blob_objects = []

        tree = self.get_tree()

        top_iter = tree.iter()

        # The bottom of the tree.
        reach_end = False

        # Start the generator:
        top_tag = next(top_iter)
        blob_objects.append(top_tag)

        # So, while we have _not_ reached the end
        while not reach_end:
            try:
                # See if this XML object has children - if not, it means we reached the end of a section.
                next_level_down = recurse_down(next(top_iter))

                # If children, then we need to go another nested layer down and retrieve those objects:
                if isinstance(next_level_down, list):

                    # recurse down again:
                    for next_level in next_level_down:
                        # if we got a valid child node element, I hate XML so much, then there's a chance this isn't
                        # the most-nested tag. Recurse down again.
                        blob_objects.append({next_level.tag: next_level.attrib})

                        # Reset the index to the next-nested object
                        next_level_down = recurse_down(next_level)
                else:
                    # If _NO_ children, we go the end of a section.
                    continue

            # HERE is where we get to the bottom of the XML tree, so break out of the for loop.
            except StopIteration:
                reach_end = True

        return blob_objects


class FormattedOutputs:

    @classmethod
    def print_brief_constraints_by_node(cls, negative_locations=True) -> str:
        """
        Print the constraints for this resource - if negative_locations, print the negative ones as well.
        """
        tree = CIBTree()

        score_parse = lambda scr: True if scr == "INFINITY" else False

        obs = []
        cib_nodes = []
        o = {
            "resource": None,
            "allowed": [],
            "disallowed": []
        }
        for node in tree.get_node_attrib_iter():
            if node.get("uname"):
                cib_nodes.append(node.get("uname"))
        print("Discovered {} node unames.".format(len(cib_nodes)))

        for constraint in tree.get_constraint_attrib_iter():
            if not o.get("name"):
                o["name"] = constraint.get("rsc")
            if score_parse(constraint.get("score")):
                print("{} allowed on {}".format(constraint.get("rsc"), constraint.get("node")))
                o["allowed"].append(constraint.get("node"))
            else:
                if negative_locations:
                    print("{} disallowed on {}".format(constraint.get("rsc"), constraint.get("node")))
                    o["disallowed"].append(constraint.get("node"))
            if len(o["allowed"]) + len(o["disallowed"]) == len(cib_nodes):
                obs.append(o)
                o = {"resource": None, "allowed": [], "disallowed": []}

        return "Parsed constraints for nodes: {}".format(", ".join(cib_nodes))

    @classmethod
    def print_detailed_resource_overview(cls):
        """Print resource """
        tree = CIBTree()
        resource_xml_list = []

        for frame in tree.get_cib_config().iter():
            if frame.tag in ["primitive", "clone", "master"]:
                for child in frame.getchildren():
                    if child.attrib:
                        for key, value in child.attrib.items():
                            ln = "{} {:20s}: {:20s} ]".format(frame.tag, str(key), str(value))
                            print(ln)
                            resource_xml_list.append(ln)
        return resource_xml_list

    @classmethod
    def print_basic_resource_overview(cls, resource):
        tree = CIBTree()
        cnst = tree.get_cib_resource_constraints(resource)

        for key, value in cnst.items():
            if isinstance(value, list):
                value = ", ".join(value)
            print("{:20s}: {:>}".format(key, str(value)))
        return cnst

    @classmethod
    def print_cib_tree(cls):
        alltags = []
        tree = CIBTree()

        blobs = tree.recurse_tree()

        for tree_elem in blobs:
            for tag, attr in tree_elem.items():
                if not tag in alltags:
                    alltags.append(tag)
                if isinstance(attr, str):
                    print("\t{:20s}".format(attr))
                elif isinstance(attr, dict):
                    for key, value in attr.items():
                        print("\t[ {} ] {:20s}: {}".format(tag, str(key), str(value)))
        print("\n - ".join(alltags))
        return alltags
