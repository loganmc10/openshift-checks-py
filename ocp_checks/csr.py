# This check looks for pending Certificate Signing Requests
import ocp_utils
import argparse
from tabulate import tabulate
from typing import Dict, Any, List


def do_check(args: argparse.Namespace) -> str:
    passed = True
    pending_csrs: List[List[str]] = []
    for csr in ocp_utils.api.CertificateSigningRequest.get()[
        "items"
    ]:  # type: Dict[str, Any]
        if not csr.get("status"):
            pending_csrs.append([csr["metadata"]["name"]])

    if pending_csrs:
        passed = False
        if not args.results_only:
            table_headers = ["PENDING CSRS"]
            print(tabulate(pending_csrs, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
