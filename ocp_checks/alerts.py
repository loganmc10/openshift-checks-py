# This check looks for Warning and Critical alerts that are firing on the cluster
import argparse
from tabulate import tabulate
from typing import Dict, Any, List
import ocp_utils


# OpenShift uses Prometheus for alerts
# These alerts aren't available via the Kubernetes API, Prometheus has its own API
# We gather alerts from Prometheus rather than Alertmanager, since the user may disable Alertmanager
def do_check(args: argparse.Namespace) -> str:
    passed = True
    bad_alerts: List[List[str]] = []
    for alert in ocp_utils.api.GetAlerts():  # type: Dict[str, Any]
        if alert["labels"]["alertname"] == "AlertmanagerReceiversNotConfigured":
            # Many people don't configure a receiver for Alertmanager, probably shouldn't fail them for this
            continue
        elif (
            alert["labels"]["alertname"].startswith("PodDisruptionBudget")
            and ocp_utils.utils.is_sno()
        ):
            # Disrupted pods have nowhere to go on SNO, and some built-in PDBs fail this test on SNO
            continue
        elif alert["labels"]["alertname"] == "ClusterNotUpgradeable":
            # Not a serious issue
            continue
        if (
            alert["labels"].get("severity") == "warning"
            or alert["labels"].get("severity") == "critical"
        ):
            message = alert["annotations"].get(
                "description",
                alert["annotations"].get(
                    "message", alert["annotations"].get("summary", "")
                ),
            )
            bad_alerts.append(
                [
                    alert["labels"]["alertname"],
                    f"{ocp_utils.utils.oc_colors['RED']}{alert['labels']['severity']}{ocp_utils.utils.oc_colors['ENDC']}",
                    alert["labels"].get("namespace", ""),
                    message,
                ]
            )

    if bad_alerts:
        passed = False
        if not args.results_only:
            table_headers = ["ALERT", "SEVERITY", "NAMESPACE", "MESSAGE"]
            print(tabulate(bad_alerts, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
