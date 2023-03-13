# This check makes sure that the reserved CPU usage is not too high
# See https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/#system-reserved
import ocp_utils
import argparse
from kubernetes import utils  # type: ignore
from tabulate import tabulate
from decimal import Decimal
from typing import Dict, Any, List  # noqa F401

query_range = "5m"


def do_check(args: argparse.Namespace) -> str:
    if args.skip_prometheus:
        return ocp_utils.utils.SKIP()

    passed = True
    bad_nodes: List[List[str]] = []
    for node in ocp_utils.utils.nodes:  # type: Dict[str, Any]
        reserved_cpu_count = utils.parse_quantity(
            node["status"]["capacity"]["cpu"]
        ) - utils.parse_quantity(node["status"]["allocatable"]["cpu"])
        if reserved_cpu_count < Decimal(1):
            # Node does not have any reserved CPUs
            continue
        used_percent = (
            Decimal(
                ocp_utils.api.do_prom_query(
                    f'rate(container_cpu_usage_seconds_total{{node="{node["metadata"]["name"]}",id="/system.slice"}}[{query_range}])'
                )[0]["value"][1]
            )
            / reserved_cpu_count
            * Decimal(100)
        )
        if used_percent > Decimal(args.reserved_cpu_threshold):
            bad_nodes.append(
                [
                    node["metadata"]["name"],
                    f"{ocp_utils.utils.oc_colors['RED']}{used_percent}{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )

    if bad_nodes:
        passed = False
        if not args.results_only:
            table_headers = ["NODE", "RESERVED CPU USAGE (%)"]
            print(tabulate(bad_nodes, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
