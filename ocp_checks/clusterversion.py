# This check makes sure the cluster version is stable
import ocp_utils
import argparse


def do_check(args: argparse.Namespace) -> str:
    passed = True
    try:
        failing_condition = next(
            item
            for item in ocp_utils.api.ClusterVersion.get(name="version")["status"][
                "conditions"
            ]
            if item["type"] == "Failing"
        )
    except ValueError:
        # If we are reading a must-gather that doesn't include cluster scoped resources, we'll end up here
        return ocp_utils.utils.SKIP()

    if failing_condition["status"] == "True":
        passed = False
        print(
            f"Cluster version failing with message: {ocp_utils.utils.oc_colors['RED']}{failing_condition.get('message', 'No message')}{ocp_utils.utils.oc_colors['ENDC']}"
        )
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
