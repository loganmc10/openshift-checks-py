# This check makes sure that the SR-IOV node state on each node is good
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List


def do_check(args: argparse.Namespace) -> str:
    if not ocp_utils.utils.supports_sriov():
        return ocp_utils.utils.SKIP()

    passed = True
    bad_sriov: List[List[str]] = []
    for sriov_state in ocp_utils.api.SriovNetworkNodeState.get(
        namespace="openshift-sriov-network-operator"
    )[
        "items"
    ]:  # type: Dict[str, Any]
        if sriov_state["status"]["syncStatus"] != "Succeeded":
            bad_sriov.append(
                [
                    sriov_state["metadata"]["name"],
                    f"{ocp_utils.utils.oc_colors['RED']}{sriov_state['status']['syncStatus']}{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )

    if bad_sriov:
        passed = False
        if not args.results_only:
            table_headers = ["NODE", "STATUS"]
            print(tabulate(bad_sriov, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
