# This check makes sure the DNS endpoints for the cluster exist
import ocp_utils
import argparse
import socket
from tabulate import tabulate
from typing import List


# Test VIP accessibility (IPv6 and IPv6)
def do_check(args: argparse.Namespace) -> str:
    if args.must_gather:
        return ocp_utils.utils.SKIP()

    passed = True
    dns_issues: List[List[str]] = []
    base_domain = ocp_utils.api.DNS.get(name="cluster")["spec"]["baseDomain"]
    test_addresses: List[str] = [f"api.{base_domain}", f"foobar.apps.{base_domain}"]
    families: List[socket.AddressFamily] = []
    if ocp_utils.utils.supports_ipv4():
        families.append(socket.AF_INET)
    if ocp_utils.utils.supports_ipv6():
        families.append(socket.AF_INET6)
    for socket_family in families:  # type: socket.AddressFamily
        for address in test_addresses:  # type: str
            try:
                socket.getaddrinfo(address, None, family=socket_family)
                with socket.socket(socket_family, socket.SOCK_STREAM) as sock:
                    if "api." in address:
                        sock.connect((address, 6443))
                    elif "apps." in address:
                        sock.connect((address, 443))
            except OSError:
                dns_issues.append(
                    [
                        base_domain,
                        f"{ocp_utils.utils.oc_colors['RED']}{address}{ocp_utils.utils.oc_colors['ENDC']}",
                        "IPv4" if socket_family == socket.AF_INET else "IPv6",
                    ]
                )

    if dns_issues:
        passed = False
        if not args.results_only:
            table_headers = ["BASE DOMAIN", "UNREACHABLE DNS NAME", "ADDRESS FAMILY"]
            print(tabulate(dns_issues, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
