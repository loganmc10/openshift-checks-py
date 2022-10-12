# This check looks for cluster operators, and user installed operators, that are not in a good state
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List


def do_check(args: argparse.Namespace) -> str:
    passed = True
    bad_operators: List[List[str]] = []
    for cluster_operator in ocp_utils.api.ClusterOperator.get()[
        "items"
    ]:  # type: Dict[str, Any]
        for condition in cluster_operator["status"][
            "conditions"
        ]:  # type: Dict[str, str]
            if (
                condition["type"] == "Degraded" or condition["type"] == "Progressing"
            ) and condition["status"] != "False":
                bad_operators.append(
                    [
                        cluster_operator["metadata"]["name"],
                        "Cluster Operator",
                        f"{ocp_utils.utils.oc_colors['RED']}{condition['type']}{ocp_utils.utils.oc_colors['ENDC']}",
                    ]
                )
            if condition["type"] == "Available" and condition["status"] != "True":
                bad_operators.append(
                    [
                        cluster_operator["metadata"]["name"],
                        "Cluster Operator",
                        f"{ocp_utils.utils.oc_colors['RED']}Not Available{ocp_utils.utils.oc_colors['ENDC']}",
                    ]
                )

    for operator in ocp_utils.api.ClusterServiceVersion.get(
        label_selector="!olm.copiedFrom"
    )[
        "items"
    ]:  # type: Dict[str, Any]
        if operator["status"]["phase"] != "Succeeded":
            bad_operators.append(
                [
                    operator["metadata"]["name"],
                    operator["metadata"].get("namespace", ""),
                    f"{ocp_utils.utils.oc_colors['RED']}{operator['status']['phase']}{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )

    if bad_operators:
        passed = False
        if not args.results_only:
            table_headers = ["OPERATOR", "NAMESPACE", "ISSUE"]
            print(tabulate(bad_operators, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
