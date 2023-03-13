# This check lists available updates for the cluster and the operators
import ocp_utils
import argparse
from typing import List, Dict, Any  # noqa F401
from tabulate import tabulate
from packaging import version


def check_cv(updates: List[List[str]]) -> None:
    latest_cv_update = ""
    cv = ocp_utils.api.ClusterVersion.get(name="version")
    if cv["status"].get("availableUpdates"):
        for cv_update in cv["status"]["availableUpdates"]:  # type: Dict[str, str]
            if version.parse(cv_update["version"]) > version.parse(latest_cv_update):
                latest_cv_update = cv_update["version"]
    if latest_cv_update:
        updates.append(
            [
                "Cluster Version",
                cv["status"]["desired"]["version"],
                latest_cv_update,
                cv["spec"]["channel"],
                f"https://amd64.ocp.releases.ci.openshift.org/releasestream/4-stable/release/{latest_cv_update}?from={cv['status']['desired']['version']}",
            ]
        )


def check_operators(updates: List[List[str]]) -> None:
    for sub in ocp_utils.api.Subscription.get()["items"]:  # type: Dict[str, Any]
        message = ""
        for condition in sub["status"]["conditions"]:  # type: Dict[str, str]
            if (
                condition["type"] == "ResolutionFailed"
                or condition["type"] == "CatalogSourcesUnhealthy"
            ) and condition["status"] == "True":
                message = condition["message"]

        if (
            sub["status"].get("currentCSV") != sub["status"].get("installedCSV")
            or message
        ):
            updates.append(
                [
                    sub["spec"]["name"],
                    sub["status"].get("installedCSV", ""),
                    sub["status"].get("currentCSV", ""),
                    sub["spec"]["channel"],
                    message,
                ]
            )


def do_check(args: argparse.Namespace) -> str:
    passed = True
    updates: List[List[str]] = []
    try:
        check_cv(updates)
        check_operators(updates)
    except ValueError:
        # If we are reading a must-gather that doesn't include cluster scoped resources, we'll end up here
        return ocp_utils.utils.SKIP()

    if updates:
        passed = False
        if not args.results_only:
            table_headers = [
                "OBJECT",
                "CURRENT VERSION",
                "LATEST VERSION",
                "CHANNEL",
                "NOTES",
            ]
            print(tabulate(updates, headers=table_headers, floatfmt=".2f"))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.INFO()
