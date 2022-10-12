# This check looks for events within the last hour in user namespaces that are not Normal
import ocp_utils
import argparse
import dateutil.parser
from tabulate import tabulate
from datetime import timedelta
from operator import itemgetter
from typing import Dict, Any, List


def do_check(args: argparse.Namespace) -> str:
    passed = True
    bad_events: List[List[str]] = []
    current_time = ocp_utils.api.GetCurrentTime()
    for user_namespace in ocp_utils.utils.user_namespaces:  # type: Dict[str, Any]
        for event in ocp_utils.api.Event.get(
            namespace=user_namespace["metadata"]["name"],
            field_selector="type!=Normal",
        )[
            "items"
        ]:  # type: Dict[str, Any]
            if event.get("lastTimestamp") is None:
                continue
            event_age = current_time - dateutil.parser.parse(event["lastTimestamp"])
            if event_age < timedelta(hours=1):
                bad_events.append(
                    [
                        f"{event['involvedObject']['kind']}/{event['involvedObject']['name']}",
                        event["involvedObject"].get("namespace", ""),
                        f"{ocp_utils.utils.oc_colors['RED']}{event['type']}{ocp_utils.utils.oc_colors['ENDC']}",
                        event["lastTimestamp"],
                        event["message"],
                    ]
                )

    bad_events = sorted(bad_events, key=itemgetter(3))  # sort by timestamp
    if bad_events:
        passed = False
        if not args.results_only:
            table_headers = [
                "OBJECT",
                "NAMEPSPACE",
                "SEVERITY",
                "TIMESTAMP",
                "MESSAGE",
            ]
            print(tabulate(bad_events, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
