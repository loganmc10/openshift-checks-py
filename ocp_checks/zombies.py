# This check finds nodes with a high number of defunct/zombie processes
# This can sometimes indicate an issue with exec probes
import ocp_utils
import argparse
import concurrent.futures
import subprocess  # nosec
from typing import Tuple, Dict, Any, List
from tabulate import tabulate


def check_node_zombies(node_name: str) -> Tuple[str, int]:
    output = subprocess.run(  # nosec
        [
            "oc",
            "debug",
            f"node/{node_name}",
            "--",
            "chroot",
            "/host",
            "sh",
            "-c",
            "ps -ef | grep -c '[d]efunct'",
        ],
        capture_output=True,
    )
    try:
        zombies = int(output.stdout.decode())
    except ValueError:
        return node_name, -1

    return node_name, zombies


def do_check(args: argparse.Namespace) -> str:
    if args.skip_oc_debug:
        return ocp_utils.utils.SKIP()

    passed = True
    node_with_zombies: List[List[str]] = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=args.parallel_jobs
    ) as executor:
        tasks = []
        for node in ocp_utils.utils.ready_nodes():  # type: Dict[str, Any]
            tasks.append(executor.submit(check_node_zombies, node["metadata"]["name"]))
        for task in concurrent.futures.as_completed(tasks):
            node_name, zombies = task.result()
            if zombies > args.zombie_threshold or zombies == -1:
                node_with_zombies.append(
                    [
                        node_name,
                        f"{ocp_utils.utils.oc_colors['RED']}{zombies if zombies > -1 else 'ERROR'}{ocp_utils.utils.oc_colors['ENDC']}",
                    ]
                )

    if node_with_zombies:
        passed = False
        if not args.results_only:
            table_headers = ["NODE", "ZOMBIE PROCESSES"]
            print(tabulate(node_with_zombies, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
