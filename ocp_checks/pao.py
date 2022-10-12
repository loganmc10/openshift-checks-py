# This check look for PerformanceProfiles that don't look good
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List


def do_check(args: argparse.Namespace) -> str:
    if not ocp_utils.utils.supports_pao():
        return ocp_utils.utils.SKIP()

    passed = True
    degraded_perfprofile: List[List[str]] = []
    for perfprofile in ocp_utils.api.PerformanceProfile.get()[
        "items"
    ]:  # type: Dict[str, Any]
        degraded_condition = next(
            item
            for item in perfprofile["status"]["conditions"]
            if item["type"] == "Degraded"
        )
        if degraded_condition["status"] != "False":
            degraded_perfprofile.append(
                [
                    perfprofile["metadata"]["name"],
                    f"{ocp_utils.utils.oc_colors['RED']}{degraded_condition.get('message', 'No message')}{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )

    if degraded_perfprofile:
        passed = False
        if not args.results_only:
            table_headers = ["FAILED PERFORMANCE PROFILE", "MESSAGE"]
            print(tabulate(degraded_perfprofile, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
