# This check looks for node interfaces with a high percentage of transmit or receive errors in the last hour
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
    queries: List[List[str]] = [
        [
            "node_network_transmit_errs_total",
            "node_network_transmit_packets_total",
            "Transmit Errors",
        ],
        [
            "node_network_transmit_drop_total",
            "node_network_transmit_packets_total",
            "Transmit Drops",
        ],
        [
            "node_network_receive_errs_total",
            "node_network_receive_packets_total",
            "Receive Errors",
        ],
        [
            "node_network_receive_drop_total",
            "node_network_receive_packets_total",
            "Receive Drops",
        ],
    ]
    for query in queries:  # type: List[str]
        for metric in ocp_utils.api.do_prom_query(
            f"( rate({query[0]}[{query_range}]) / (rate({query[1]}[{query_range}]) > 0) ) > {args.network_threshold / Decimal(100)}"
        ):  # type: Dict[str, Any]
            bad_interfaces.append(
                [
                    metric["metric"]["instance"],
                    metric["metric"]["device"],
                    f"{ocp_utils.utils.oc_colors['RED']}{query[2]}{ocp_utils.utils.oc_colors['ENDC']}",
                    str(Decimal(metric["value"][1]) * Decimal(100)),
                ]
            )

    if bad_interfaces:
        passed = False
        if not args.results_only:
            table_headers = [
                "NODE",
                "INTERFACE",
                "ISSUE",
                f"RATE (%) OVER {query_range}",
            ]
            print(tabulate(bad_interfaces, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
