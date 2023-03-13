# Looks for pods that are not up, or jobs that have failed
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List  # noqa F401


def do_check(args: argparse.Namespace) -> str:
    passed = True
    bad_pods: List[List[str]] = []
    for pod in ocp_utils.api.Pod.get(
        field_selector="status.phase!=Running,status.phase!=Succeeded,metadata.namespace!=checks-openshift"
    )[
        "items"
    ]:  # type: Dict[str, Any]
        try:
            ready_condition = next(
                item for item in pod["status"]["conditions"] if item["type"] == "Ready"
            )
        except StopIteration:
            ready_condition = next(
                item
                for item in pod["status"]["conditions"]
                if item["type"] == "PodScheduled"
            )
        except TypeError:
            ready_condition = pod["status"]
        bad_pods.append(
            [
                pod["metadata"]["name"],
                pod["metadata"]["namespace"],
                f"{ocp_utils.utils.oc_colors['RED']}{pod['status']['phase']}{ocp_utils.utils.oc_colors['ENDC']}",
                ready_condition.get("message", "No message"),
            ]
        )

    if bad_pods:
        passed = False
        if not args.results_only:
            table_headers = ["POD", "NAMEPSPACE", "STATUS", "REASON"]
            print(tabulate(bad_pods, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
