# This check looks for master/control nodes that are schedulable
# In some cases this is acceptable, and this check can be skipped
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List  # noqa F401


def do_check(args: argparse.Namespace) -> str:
    if ocp_utils.utils.is_sno():
        return ocp_utils.utils.SKIP()

    passed = True
    scheduable_controllers: List[List[str]] = []
    for node in ocp_utils.utils.nodes:  # type: Dict[str, Any]
        if node["metadata"]["labels"].get(
            "node-role.kubernetes.io/master"
        ) == "" and not node["spec"].get("taints"):
            scheduable_controllers.append([node["metadata"]["name"]])

    if scheduable_controllers:
        passed = False
        if not args.results_only:
            table_headers = ["SCHEDUABLE CONTROLLER"]
            print(tabulate(scheduable_controllers, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.INFO()
