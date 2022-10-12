from typing import List, Dict, Any
import ocp_utils.api
import argparse
from kubernetes import config  # type: ignore


nodes: List[Dict[str, Any]] = []
pods: List[Dict[str, Any]] = []
user_namespaces: List[Dict[str, Any]] = []

oc_colors = {
    "RED": "\033[0;31m",
    "GREEN": "\033[0;32m",
    "ORANGE": "\033[0;33m",
    "BLUE": "\033[0;34m",
    "PURPLE": "\033[0;35m",
    "CYAN": "\033[0;36m",
    "YELLOW": "\033[1;33m",
    "ENDC": "\033[0m",
}


def PASS() -> str:
    return f"{oc_colors['GREEN']}PASS{oc_colors['ENDC']}"


def FAIL() -> str:
    return f"{oc_colors['RED']}FAIL{oc_colors['ENDC']}"


def INFO() -> str:
    return f"{oc_colors['BLUE']}INFO{oc_colors['ENDC']}"


def SKIP() -> str:
    return f"{oc_colors['ORANGE']}SKIP{oc_colors['ENDC']}"


def ERROR() -> str:
    return f"{oc_colors['YELLOW']}ERROR{oc_colors['ENDC']}"


# Getting a list of Ready nodes is useful if you want to use oc debug
# There is no point trying to connect to a node that isn't up
def ready_nodes() -> List[Dict[str, Any]]:
    ready_nodes_list: List[Dict[str, Any]] = []
    for node in nodes:  # type: Dict[str, Any]
        # This if statement loops through the node status conditions, looking for one with a type of "Ready" and a status of "True"
        if (
            next(
                item for item in node["status"]["conditions"] if item["type"] == "Ready"
            )["status"]
            == "True"
        ):
            ready_nodes_list.append(node)
    return ready_nodes_list


def is_sno() -> bool:
    return True if len(nodes) == 1 else False


def is_ovn() -> bool:
    try:
        clusternetwork = ocp_utils.api.Network.get(name="cluster")
        if clusternetwork["spec"]["networkType"] == "OVNKubernetes":
            return True
        else:
            return False
    except ValueError:
        # If we are reading a must-gather that doesn't include cluster scoped resources, we'll end up here
        return False


def supports_ipv4() -> bool:
    clusternetwork = ocp_utils.api.Network.get(name="cluster")
    for network in clusternetwork["spec"]["clusterNetwork"]:  # type: Dict[str, str]
        if "." in network["cidr"]:
            return True
    return False


def supports_ipv6() -> bool:
    clusternetwork = ocp_utils.api.Network.get(name="cluster")
    for network in clusternetwork["spec"]["clusterNetwork"]:  # type: Dict[str, str]
        if ":" in network["cidr"]:
            return True
    return False


def supports_sriov() -> bool:
    try:
        ocp_utils.api.CustomResourceDefinition.get(
            name="sriovnetworknodestates.sriovnetwork.openshift.io"
        )
        return True
    except Exception:
        return False


def supports_pao() -> bool:
    try:
        ocp_utils.api.CustomResourceDefinition.get(
            name="performanceprofiles.performance.openshift.io"
        )
        return True
    except Exception:
        return False


# Pre-cache some API data so that we don't ask for it multiple times
def init(args: argparse.Namespace) -> None:
    if not args.must_gather:
        if args.incluster_config:
            k8s_config = config.load_incluster_config()
        else:
            k8s_config = config.load_kube_config()
        ocp_utils.api.init_api(args, k8s_config)
    else:
        ocp_utils.api.init_must_gather(args)
    nodes.extend(ocp_utils.api.Node.get()["items"])
    pods.extend(ocp_utils.api.Pod.get()["items"])
    for namespace in ocp_utils.api.Namespace.get()["items"]:  # type: Dict[str, Any]
        if (
            not namespace["metadata"]["name"].startswith("kube-")
            and not namespace["metadata"]["name"].startswith("openshift-")
            and not namespace["metadata"]["name"] == "default"
            and not namespace["metadata"]["name"] == "openshift"
        ):
            user_namespaces.append(namespace)
