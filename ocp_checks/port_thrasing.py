# Detects port thrasing in OVN Kubernetes, fixed in more recent versions
import ocp_utils
import ocp_utils.api
import argparse
from tabulate import tabulate
from typing import Dict, Any, List  # noqa F401


def do_check(args: argparse.Namespace) -> str:
    if not ocp_utils.utils.is_ovn():
        return ocp_utils.utils.SKIP()

    passed = True
    thrasing_pods: List[List[str]] = []
    for pod in ocp_utils.api.Pod.get(
        namespace="openshift-ovn-kubernetes", label_selector="app=ovnkube-node"
    )[
        "items"
    ]:  # type: Dict[str, Any]
        thrasing_messages = ocp_utils.api.ReadPodLogs(
            namespace="openshift-ovn-kubernetes",
            name=pod["metadata"]["name"],
            container="ovn-controller",
        ).count("Changing chassis for lport")

        if thrasing_messages > args.port_thrasing_threshold:
            thrasing_pods.append(
                [
                    pod["metadata"]["name"],
                    pod["spec"]["nodeName"],
                    f"{ocp_utils.utils.oc_colors['RED']}{thrasing_messages}{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )

    if thrasing_pods:
        passed = False
        if not args.results_only:
            table_headers = [
                "POD",
                "NODE",
                "THRASING MESSAGES",
            ]
            print(tabulate(thrasing_pods, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
