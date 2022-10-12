# This check looks for nodes that are not ready, or are not schedulable, or have disk/memory/PID pressure
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List


def do_check(args: argparse.Namespace) -> str:
    passed = True
    bad_nodes: List[List[str]] = []
    for node in ocp_utils.utils.nodes:  # type: Dict[str, Any]
        if (
            next(
                item for item in node["status"]["conditions"] if item["type"] == "Ready"
            )["status"]
            != "True"
        ):
            bad_nodes.append(
                [
                    node["metadata"]["name"],
                    f"{ocp_utils.utils.oc_colors['RED']}Not Ready{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )
        if node["spec"].get("unschedulable") is not None:
            bad_nodes.append(
                [
                    node["metadata"]["name"],
                    f"{ocp_utils.utils.oc_colors['RED']}Unschedulable{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )
        for item in node["status"]["conditions"]:  # type: Dict[str, str]
            if "Pressure" in item["type"] and item["status"] != "False":
                bad_nodes.append(
                    [
                        node["metadata"]["name"],
                        f"{ocp_utils.utils.oc_colors['RED']}{item['type']}{ocp_utils.utils.oc_colors['ENDC']}",
                    ]
                )

    if bad_nodes:
        passed = False
        if not args.results_only:
            table_headers = ["NODE", "ISSUE"]
            print(tabulate(bad_nodes, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
