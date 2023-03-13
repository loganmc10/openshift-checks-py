# This check look for PodNetworkConnectivityChecks that don't look good
import ocp_utils
import argparse
from kubernetes import dynamic  # type: ignore
from tabulate import tabulate
from typing import Dict, Any, List  # noqa F401


def do_check(args: argparse.Namespace) -> str:
    passed = True
    bad_connectivity: List[List[str]] = []
    try:
        connectivity_checks = ocp_utils.api.PodNetworkConnectivityCheck.get(
            namespace="openshift-network-diagnostics"
        )
    except dynamic.exceptions.ForbiddenError:
        return ocp_utils.utils.SKIP()
    for connectivity_check in connectivity_checks["items"]:  # type: Dict[str, Any]
        try:
            reachable_condition = next(
                item
                for item in connectivity_check["status"]["conditions"]
                if item["type"] == "Reachable"
            )
        except TypeError:
            continue
        if reachable_condition["status"] != "True":
            bad_connectivity.append(
                [
                    connectivity_check["metadata"]["name"],
                    reachable_condition.get("message", "No message"),
                ]
            )

    if bad_connectivity:
        passed = False
        if not args.results_only:
            table_headers = ["CHECK", "MESSAGE"]
            print(tabulate(bad_connectivity, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
