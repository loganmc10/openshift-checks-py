# This check finds containers that have restarted within the last 24h and prints the reason
import ocp_utils
import argparse
import dateutil.parser
from tabulate import tabulate
from datetime import timedelta
from typing import Dict, Any, List


def do_check(args: argparse.Namespace) -> str:
    passed = True
    bad_containers: List[List[str]] = []
    current_time = ocp_utils.api.GetCurrentTime()
    for pod in ocp_utils.utils.pods:  # type: Dict[str, Any]
        for container in pod["status"].get(
            "containerStatuses", []
        ):  # type: Dict[str, Any]
            if container["lastState"].get("terminated"):
                try:
                    event_age = current_time - dateutil.parser.parse(
                        container["lastState"]["terminated"]["finishedAt"]
                    )
                except TypeError:
                    continue
                if container["lastState"]["terminated"][
                    "reason"
                ] != "Completed" and event_age < timedelta(hours=24):
                    bad_containers.append(
                        [
                            pod["metadata"]["name"],
                            pod["metadata"]["namespace"],
                            container["name"],
                            f"{ocp_utils.utils.oc_colors['RED']}{container['lastState']['terminated']['reason']}{ocp_utils.utils.oc_colors['ENDC']}",
                        ]
                    )

    if bad_containers:
        passed = False
        if not args.results_only:
            table_headers = [
                "POD",
                "NAMEPSPACE",
                "TERMINATED CONTAINER",
                "REASON",
            ]
            print(tabulate(bad_containers, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
