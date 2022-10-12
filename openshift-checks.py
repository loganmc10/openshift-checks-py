#!/usr/bin/env python3
import argparse
import sys
import os
import ocp_checks
import ocp_utils

funcs = [
    ocp_checks.cluster_dns.do_check,
    ocp_checks.alerts.do_check,
    ocp_checks.bad_kernel.do_check,
    ocp_checks.clusterversion.do_check,
    ocp_checks.connectivity.do_check,
    ocp_checks.csr.do_check,
    ocp_checks.ctrlnodes.do_check,
    ocp_checks.entropy.do_check,
    ocp_checks.ethernet_firmware.do_check,
    ocp_checks.events.do_check,
    ocp_checks.kubelet.do_check,
    ocp_checks.link_flapping.do_check,
    ocp_checks.mcp.do_check,
    ocp_checks.network.do_check,
    ocp_checks.nodes.do_check,
    ocp_checks.notrunningpods.do_check,
    ocp_checks.operators.do_check,
    ocp_checks.ovn_pod_memory_usage.do_check,
    ocp_checks.pao.do_check,
    ocp_checks.port_thrasing.do_check,
    ocp_checks.pvc.do_check,
    ocp_checks.reserved_cpu_usage.do_check,
    ocp_checks.restarts.do_check,
    ocp_checks.sriov.do_check,
    ocp_checks.terminating.do_check,
    ocp_checks.zombies.do_check,
    ocp_checks.updates.do_check,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Perform a health check on an OpenShift cluster."
    )
    parser.add_argument(
        "-n", "--no-colors", action="store_true", help="Disable colored output"
    )
    parser.add_argument("-s", "--single", type=str, help="Run a single check")
    parser.add_argument("-l", "--list", action="store_true", help="List checks")
    parser.add_argument(
        "-r", "--results-only", action="store_true", help="Only show results"
    )
    parser.add_argument(
        "-p",
        "--parallel-jobs",
        type=int,
        default=3,
        help="How many oc debug jobs to run in parallel. Default=3",
    )
    parser.add_argument(
        "-i", "--incluster-config", action="store_true", help="Use in-cluster config"
    )
    parser.add_argument(
        "--skip", type=str, default="", help="Comma separated list of checks to skip"
    )
    parser.add_argument(
        "--skip-oc-debug", action="store_true", help="Skip checks that use oc debug"
    )
    parser.add_argument(
        "--skip-prometheus", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "-m", "--must-gather", type=str, help="Path to a must-gather folder"
    )
    parser.add_argument(
        "--entropy-threshold",
        type=int,
        default=200,
        help="Entropy threshold in bits. Default=200",
    )
    parser.add_argument(
        "--ovn-memory-threshold",
        type=int,
        default=5000,
        help="OVN pod memory threshold in Mi. Default=5000",
    )
    parser.add_argument(
        "--port-thrasing-threshold",
        type=int,
        default=10,
        help="OVN port thrasing message threshold. Default=10",
    )
    parser.add_argument(
        "--reserved-cpu-threshold",
        type=int,
        default=80,
        help="Reserved CPU usage threshold in percent. Default=80",
    )
    parser.add_argument(
        "--zombie-threshold",
        type=int,
        default=5,
        help="Zombie process count threshold. Default=5",
    )
    parser.add_argument(
        "--network-threshold",
        type=int,
        default=1,
        help="Network error/drop threshold in percent. Default=1",
    )
    parser.add_argument(
        "--flap-threshold",
        type=int,
        default=5,
        help="Interface flapping threshold. Default=5",
    )
    return parser.parse_args()


def main() -> None:
    return_code = os.EX_OK
    args = parse_args()
    if args.must_gather:
        args.skip_oc_debug = True
        args.skip_prometheus = True
    if args.list:
        for fn in funcs:
            print(f"{fn.__module__.split('.')[1]}")
        sys.exit(return_code)

    if args.no_colors is True:
        # This clears out all the string values in the colors dict
        ocp_utils.utils.oc_colors = ocp_utils.utils.oc_colors.fromkeys(
            ocp_utils.utils.oc_colors, ""
        )

    try:
        if not args.results_only:
            print("Initializing...")
        ocp_utils.utils.init(args)
    except Exception as e:
        print(f"Error {e.__class__.__name__} in initialization:\n{e}")
        sys.exit(os.EX_OSERR)
    # Loop through each of the check functions defined above
    # Functions return a string that is displayed to the user (normally PASS or FAIL)
    func_count = 0
    for fn in funcs:
        check_name = fn.__module__.split(".")[1]
        if check_name == args.single or not args.single:
            func_count += 1
            if not args.results_only:
                print(f"\nRunning check: {check_name}")
            if check_name in args.skip.split(","):
                print(f"{check_name: <30} {ocp_utils.utils.SKIP()}")
            else:
                try:
                    result = fn(args)
                except Exception as e:
                    print(
                        f"{ocp_utils.utils.oc_colors['RED']}Error {e.__class__.__name__} in check {check_name}:{ocp_utils.utils.oc_colors['ENDC']}\n{e}"
                    )
                    continue
                print(f"{check_name: <30} {result}")
                if result == ocp_utils.utils.FAIL() and return_code != os.EX_OSERR:
                    return_code = os.EX_SOFTWARE
                elif result == ocp_utils.utils.ERROR():
                    return_code = os.EX_OSERR
    if args.single and func_count == 0:
        print("Check not found")
        return_code = os.EX_USAGE
    sys.exit(return_code)


if __name__ == "__main__":
    main()
