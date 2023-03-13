# This check looks for ethernet cards with firmware below the recommended version
# See https://github.com/openshift/sriov-network-operator/blob/master/deploy/configmap.yaml
# See this for Mellanox (Supported HCAs Firmware Versions): https://network.nvidia.com/pdf/prod_software/Red_Hat_Enterprise_Linux_(RHEL)_8.4_Driver_Release_Notes.pdf
import ocp_utils
import argparse
import concurrent.futures
import subprocess  # nosec
from typing import Dict, List, Any  # noqa F401
from packaging import version
from tabulate import tabulate

firmware_mins: Dict[str, str] = {
    "8086:158a": "0.0",  # Intel_i40e_XXV710
    "8086:158b": "0.0",  # Intel_i40e_25G_SFP28
    "8086:1572": "0.0",  # Intel_i40e_10G_X710_SFP
    "8086:0d58": "0.0",  # Intel_i40e_XXV710_N3000
    "8086:1583": "0.0",  # Intel_i40e_40G_XL710_QSFP
    "8086:1592": "0.0",  # Intel_ice_Columbiaville_E810-CQDA2_2CQDA2
    "8086:1593": "0.0",  # Intel_ice_Columbiaville_E810-XXVDA4
    "8086:159b": "0.0",  # Intel_ice_Columbiaville_E810-XXVDA2
    "15b3:1013": "12.28.2006",  # Nvidia_mlx5_ConnectX-4
    "15b3:1015": "14.30.1004",  # Nvidia_mlx5_ConnectX-4LX
    "15b3:1017": "16.30.1004",  # Nvidia_mlx5_ConnectX-5
    "15b3:1019": "16.30.1004",  # Nvidia_mlx5_ConnectX-5_Ex
    "15b3:101b": "20.30.1004",  # Nvidia_mlx5_ConnectX-6
    "15b3:101d": "22.30.1004",  # Nvidia_mlx5_ConnectX-6_Dx
    "15b3:a2d6": "24.30.1004",  # Nvidia_mlx5_MT42822_BlueField-2_integrated_ConnectX-6_Dx
    "14e4:16d7": "0.0",  # Broadcom_bnxt_BCM57414_2x25G
    "14e4:1750": "0.0",  # Broadcom_bnxt_BCM75508_2x100G
    "1077:1654": "0.0",  # Qlogic_qede_QL45000_50G
}


def check_node_firmware(
    node_name: str, physical_interface_firmwares: Dict[str, str]
) -> List[List[str]]:
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
            f"for interface in {' '.join(physical_interface_firmwares.keys())}; do echo START: $interface; ethtool -i $interface; done",
        ],
        capture_output=True,
    )

    firmwares: List[Dict[str, str]] = []
    for line in output.stdout.decode().splitlines():  # type: str
        if line.startswith("START: "):
            firmwares.append({"interface_name": line.split(": ")[1]})
            firmwares[-1]["node"] = node_name
        elif line.startswith("driver: "):
            firmwares[-1]["driver"] = line.split(": ")[1]
        elif line.startswith("firmware-version: "):
            firmwares[-1]["firmware"] = line.split(": ")[1].split(" ")[0]

    bad_firmwares: List[List[str]] = []
    for firmware in firmwares:  # type: Dict[str, str]
        if version.parse(firmware["firmware"]) < version.parse(
            physical_interface_firmwares[firmware["interface_name"]]
        ):
            bad_firmwares.append(
                [
                    firmware["node"],
                    firmware["interface_name"],
                    firmware["driver"],
                    f"{ocp_utils.utils.oc_colors['RED']}{firmware['firmware']}{ocp_utils.utils.oc_colors['ENDC']}",
                    physical_interface_firmwares[firmware["interface_name"]],
                ]
            )

    return bad_firmwares


def do_check(args: argparse.Namespace) -> str:
    if args.skip_oc_debug:
        return ocp_utils.utils.SKIP()
    if not ocp_utils.utils.supports_sriov():
        return ocp_utils.utils.SKIP()

    passed = True
    physical_interface_firmwares: Dict[str, Dict[str, str]] = {}
    for sriov_state in ocp_utils.api.SriovNetworkNodeState.get(
        namespace="openshift-sriov-network-operator",
    )[
        "items"
    ]:  # type: Dict[str, Any]
        physical_interface_firmwares[sriov_state["metadata"]["name"]] = {}
        for interface in sriov_state["status"]["interfaces"]:  # type: Dict[str, str]
            if (
                firmware_mins.get(
                    f"{interface['vendor']}:{interface['deviceID']}", "0.0"
                )
                != "0.0"
            ):
                # We only add physical interfaces to the list if we know the minimum firmware
                physical_interface_firmwares[sriov_state["metadata"]["name"]][
                    interface["name"]
                ] = firmware_mins[f"{interface['vendor']}:{interface['deviceID']}"]

    combined_bad_firmwares: List[List[str]] = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=args.parallel_jobs
    ) as executor:
        tasks = []
        for node in ocp_utils.utils.ready_nodes():  # type: Dict[str, Any]
            if physical_interface_firmwares.get(node["metadata"]["name"]):
                # Only run the check on nodes where we have found supported interfaces, and where we know the minimum firmware for those interfaces
                tasks.append(
                    executor.submit(
                        check_node_firmware,
                        node["metadata"]["name"],
                        physical_interface_firmwares[node["metadata"]["name"]],
                    )
                )
        for task in concurrent.futures.as_completed(tasks):
            combined_bad_firmwares.extend(task.result())

    if combined_bad_firmwares:
        passed = False
        if not args.results_only:
            table_headers = [
                "NODE",
                "INTERFACE",
                "DRIVER",
                "CURRENT FIRMWARE",
                "MINIMUM FIRMWARE",
            ]
            print(tabulate(combined_bad_firmwares, headers=table_headers))
    return ocp_utils.utils.PASS() if passed else ocp_utils.utils.FAIL()
