# This check looks for nodes with low entropy available
import ocp_utils
import argparse
from tabulate import tabulate
from decimal import Decimal
from typing import Dict, Any, List


def do_check(args: argparse.Namespace) -> str:
    if args.skip_prometheus:
        return ocp_utils.utils.SKIP()

    passed = True
    bad_nodes: List[List[str]] = []
    for node in ocp_utils.utils.nodes:  # type: Dict[str, Any]
        entropy_bits = Decimal(
            ocp_utils.api.do_prom_query(
                f'node_entropy_available_bits{{instance="{node["metadata"]["name"]}"}}'
            )[0]["value"][1]
        )
        if entropy_bits < Decimal(args.entropy_threshold):
            bad_nodes.append(
                [
                    node["metadata"]["name"],
                    f"{ocp_utils.utils.oc_colors['RED']}{entropy_bits}{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )

    if bad_nodes:
        passed = False
        if not args.results_only:
            table_headers = ["NODE", "ENTROPY BITS AVAILABLE"]
            print(tabulate(bad_nodes, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
