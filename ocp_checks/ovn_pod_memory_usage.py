# See KB: https://access.redhat.com/solutions/6493321
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List  # noqa F401


def do_check(args: argparse.Namespace) -> str:
    if not ocp_utils.utils.is_ovn():
        return ocp_utils.utils.SKIP()
    if args.skip_prometheus:
        return ocp_utils.utils.SKIP()

    passed = True
    bad_pods: List[List[str]] = []
    for pod_metric in ocp_utils.api.do_prom_query(
        'sum(container_memory_working_set_bytes{namespace="openshift-ovn-kubernetes", pod=~"ovnkube-node.*", container!="", image!=""}) by (pod)'
    ):  # type: Dict[str, Any]
        mem_mi = int(int(pod_metric["value"][1]) / 1024 / 1024)
        if mem_mi > args.ovn_memory_threshold:
            bad_pods.append(
                [
                    pod_metric["metric"]["pod"],
                    f"{ocp_utils.utils.oc_colors['RED']}{mem_mi}{ocp_utils.utils.oc_colors['ENDC']}",
                ]
            )

    if bad_pods:
        passed = False
        if not args.results_only:
            table_headers = ["OVN POD", "MEMORY USAGE (Mi)"]
            print(tabulate(bad_pods, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
