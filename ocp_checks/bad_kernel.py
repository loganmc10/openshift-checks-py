# This check looks for kernels in use known to be affected by bugs
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List  # noqa F401

bad_kernels = [{"bug": "bz1948052", "kernel": "4.18.0-193.24.1.el8_2.dt1.x86_64"}]


def do_check(args: argparse.Namespace) -> str:
    passed = True
    kernel_list: List[List[str]] = []
    for node in ocp_utils.utils.nodes:  # type: Dict[str, Any]
        for bad_kernel in bad_kernels:  # type: Dict[str, str]
            if node["status"]["nodeInfo"]["kernelVersion"] == bad_kernel["kernel"]:
                kernel_list.append(
                    [
                        node["metadata"]["name"],
                        bad_kernel["bug"],
                        f"{ocp_utils.utils.oc_colors['RED']}{bad_kernel['kernel']}{ocp_utils.utils.oc_colors['ENDC']}",
                    ]
                )

    if kernel_list:
        passed = False
        if not args.results_only:
            table_headers = ["NODE", "BUG", "KERNEL"]
            print(tabulate(kernel_list, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
