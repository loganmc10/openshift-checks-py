# This check look for KubeletConfigs that don't look good
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List  # noqa F401


def do_check(args: argparse.Namespace) -> str:
    passed = True
    degraded_kubeletconfig: List[List[str]] = []
    for kubeletconfig in ocp_utils.api.KubeletConfig.get()[
        "items"
    ]:  # type: Dict[str, Any]
        try:
            condition = next(
                item
                for item in kubeletconfig["status"]["conditions"]
                if item["type"] == "Success"
            )
            success_condition = condition["status"] == "True"
        except StopIteration:
            condition = next(
                item
                for item in kubeletconfig["status"]["conditions"]
                if item["type"] == "Failure"
            )
            success_condition = condition["status"] == "False"
        if not success_condition:
            degraded_kubeletconfig.append(
                [
                    kubeletconfig["metadata"]["name"],
                    f"{ocp_utils.utils.oc_colors['RED']}{condition.get('message', 'No message')}{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )

    if degraded_kubeletconfig:
        passed = False
        if not args.results_only:
            table_headers = ["FAILED KUBELET CONFIG", "MESSAGE"]
            print(tabulate(degraded_kubeletconfig, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
