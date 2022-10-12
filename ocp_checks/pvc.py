# This check finds persistent volume claims that aren't Bound
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List


def do_check(args: argparse.Namespace) -> str:
    passed = True
    bad_pvcs: List[List[str]] = []
    for pvc in ocp_utils.api.PersistentVolumeClaim.get()[
        "items"
    ]:  # type: Dict[str, Any]
        if pvc["metadata"].get("deletionTimestamp"):
            status = "Terminating"
        else:
            status = pvc["status"]["phase"]
        if status != "Bound":
            bad_pvcs.append(
                [
                    pvc["metadata"]["name"],
                    pvc["metadata"]["namespace"],
                    f"{ocp_utils.utils.oc_colors['RED']}{status}{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )

    if bad_pvcs:
        passed = False
        if not args.results_only:
            table_headers = [
                "PERSISTENT VOLUME CLAIM",
                "NAMEPSPACE",
                "STATUS",
            ]
            print(tabulate(bad_pvcs, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
