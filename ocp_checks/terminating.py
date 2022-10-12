# This check finds namespaces and pods stuck in terminating state
import ocp_utils
import argparse
from tabulate import tabulate
from typing import List


def do_check(args: argparse.Namespace) -> str:
    passed = True
    terminating_pods: List[List[str]] = []
    for pod in ocp_utils.utils.pods:
        if pod["metadata"].get("deletionTimestamp"):
            terminating_pods.append(
                [
                    pod["metadata"]["name"],
                    pod["metadata"]["namespace"],
                ]
            )

    if terminating_pods:
        passed = False
        if not args.results_only:
            table_headers = [
                "TERMINATING POD",
                "NAMEPSPACE",
            ]
            print(tabulate(terminating_pods, headers=table_headers))

    terminating_namespaces: List[List[str]] = []
    for namespace in ocp_utils.utils.user_namespaces:
        if namespace["status"].get("phase") == "Terminating":
            terminating_namespaces.append(
                [
                    namespace["metadata"]["name"],
                ]
            )

    if terminating_namespaces:
        passed = False
        if not args.results_only:
            table_headers = [
                "TERMINATING NAMESPACE",
            ]
            print(tabulate(terminating_namespaces, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
