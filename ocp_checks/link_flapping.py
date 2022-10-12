# This check looks for node interfaces that are flapping (going up and down)
import ocp_utils
import argparse
from tabulate import tabulate
from decimal import Decimal
from typing import List, Dict, Any

query_range = "1h"


def do_check(args: argparse.Namespace) -> str:
    if args.skip_prometheus:
        return ocp_utils.utils.SKIP()

    passed = True
    bad_interfaces: List[List[str]] = []
    for metric in ocp_utils.api.do_prom_query(
        f"increase(node_network_carrier_changes_total[{query_range}]) > {args.flap_threshold}"
    ):  # type: Dict[str, Any]
        bad_interfaces.append(
            [
                metric["metric"]["instance"],
                metric["metric"]["device"],
                f"{ocp_utils.utils.oc_colors['RED']}{int(Decimal(metric['value'][1]))}{ocp_utils.utils.oc_colors['ENDC']}",
            ]
        )

    if bad_interfaces:
        passed = False
        if not args.results_only:
            table_headers = ["NODE", "INTERFACE", f"FLAPS OVER {query_range}"]
            print(tabulate(bad_interfaces, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
