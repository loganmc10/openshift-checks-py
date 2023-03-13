# This check look for machines that are not up to date with their Machine Config Pool
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List  # noqa F401


def do_check(args: argparse.Namespace) -> str:
    passed = True
    degraded_mcp: List[List[str]] = []
    for mcp in ocp_utils.api.MachineConfigPool.get()["items"]:  # type: Dict[str, Any]
        if mcp["status"]["degradedMachineCount"] > 0:
            degraded_mcp.append(
                [
                    mcp["metadata"]["name"],
                    f"{ocp_utils.utils.oc_colors['RED']}{mcp['status']['degradedMachineCount']}{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )

    if degraded_mcp:
        passed = False
        if not args.results_only:
            table_headers = ["MCP", "DEGRADED MACHINE COUNT"]
            print(tabulate(degraded_mcp, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
