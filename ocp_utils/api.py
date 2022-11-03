from kubernetes import dynamic, client  # type:ignore
from typing import Any, List, Dict
from datetime import datetime, timezone
import requests
import argparse
import ocp_utils
import subprocess  # nosec
from urllib3.exceptions import InsecureRequestWarning

from ocp_utils.mustgather import MustGather

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # type: ignore
_prom_session = requests.Session()
_prom_data = {"route": "", "bearer": ""}

CertificateSigningRequest: dynamic.Resource = None
ClusterOperator: dynamic.Resource = None
ClusterServiceVersion: dynamic.Resource = None
ClusterVersion: dynamic.Resource = None
CustomResourceDefinition: dynamic.Resource = None
DNS: dynamic.Resource = None
Event: dynamic.Resource = None
MachineConfigPool: dynamic.Resource = None
Namespace: dynamic.Resource = None
Network: dynamic.Resource = None
Node: dynamic.Resource = None
PersistentVolumeClaim: dynamic.Resource = None
Pod: dynamic.Resource = None
PodNetworkConnectivityCheck: dynamic.Resource = None
Route: dynamic.Resource = None
Secret: dynamic.Resource = None
ServiceAccount: dynamic.Resource = None
SriovNetworkNodeState: dynamic.Resource = None
Subscription: dynamic.Resource = None
KubeletConfig: dynamic.Resource = None
PerformanceProfile: dynamic.Resource = None

ReadPodLogs: dynamic.Resource = None
GetAlerts: dynamic.Resource = None
GetCurrentTime: dynamic.Resource = None


def get_time() -> datetime:
    return datetime.now(timezone.utc)


def read_namespaced_pod_log(namespace: str, name: str, container: str) -> Any:
    return client.CoreV1Api().read_namespaced_pod_log(
        namespace=namespace,
        name=name,
        container=container,
    )


def _get_prom_token() -> str:
    sa_token_request = client.CoreV1Api().create_namespaced_service_account_token(
        namespace="openshift-monitoring", name="prometheus-k8s", body={}
    )
    return f"Bearer {sa_token_request.status.token}"


def _get_prom_route() -> str:
    return str(
        ocp_utils.api.Route.get(
            name="prometheus-k8s",
            namespace="openshift-monitoring",
        )["spec"]["host"]
    )


def _prom_init(bearer_token: str) -> None:
    _prom_data["route"] = _get_prom_route()
    _prom_data["bearer"] = bearer_token if bearer_token else _get_prom_token()


# Helper function to query Prometheus for metrics
def do_prom_query(query: str) -> List[Dict[str, Any]]:
    headers = {"Authorization": _prom_data["bearer"]}
    resp = _prom_session.post(
        f"https://{_prom_data['route']}/api/v1/query",
        headers=headers,
        verify=False,  # nosec
        params={"query": query},
    )
    resp.raise_for_status()
    return list(resp.json()["data"]["result"])


# Alerts are gathered from Prometheus rather than Alertmanager, since users may disable Alertmanager
def get_alerts() -> Any:
    route = Route.get(
        name="prometheus-k8s",
        namespace="openshift-monitoring",
    )
    headers = {"Authorization": _prom_data["bearer"]}
    resp = _prom_session.get(
        f"https://{route['spec']['host']}/api/v1/rules",
        headers=headers,
        verify=False,  # nosec
    )
    resp.raise_for_status()
    firing_alerts = []
    for group in resp.json()["data"]["groups"]:
        for rule in group["rules"]:
            if rule.get("type") == "alerting" and rule.get("state") == "firing":
                firing_alerts.extend(rule["alerts"])
    return firing_alerts


def init_must_gather(args: argparse.Namespace) -> None:
    ocp_utils.mustgather.mg_path = args.must_gather
    ocp_utils.mustgather.read_must_gather(args)
    ocp_utils.api.CertificateSigningRequest = MustGather(
        api_version="certificates.k8s.io/v1", kind="CertificateSigningRequest"
    )
    ocp_utils.api.ClusterOperator = MustGather(
        api_version="config.openshift.io/v1", kind="ClusterOperator"
    )
    ocp_utils.api.ClusterServiceVersion = MustGather(
        api_version="operators.coreos.com/v1alpha1", kind="ClusterServiceVersion"
    )
    ocp_utils.api.ClusterVersion = MustGather(
        api_version="config.openshift.io/v1", kind="ClusterVersion"
    )
    ocp_utils.api.CustomResourceDefinition = MustGather(
        api_version="apiextensions.k8s.io/v1", kind="CustomResourceDefinition"
    )
    ocp_utils.api.DNS = MustGather(api_version="config.openshift.io/v1", kind="DNS")
    ocp_utils.api.Event = MustGather(api_version="v1", kind="Event")
    ocp_utils.api.KubeletConfig = MustGather(
        api_version="machineconfiguration.openshift.io/v1", kind="KubeletConfig"
    )
    ocp_utils.api.MachineConfigPool = MustGather(
        api_version="machineconfiguration.openshift.io/v1", kind="MachineConfigPool"
    )
    ocp_utils.api.Namespace = MustGather(api_version="v1", kind="Namespace")
    ocp_utils.api.Network = MustGather(
        api_version="config.openshift.io/v1", kind="Network"
    )
    ocp_utils.api.Node = MustGather(api_version="v1", kind="Node")
    ocp_utils.api.PersistentVolumeClaim = MustGather(
        api_version="v1", kind="PersistentVolumeClaim"
    )
    ocp_utils.api.Pod = MustGather(api_version="v1", kind="Pod")
    ocp_utils.api.PodNetworkConnectivityCheck = MustGather(
        api_version="controlplane.operator.openshift.io/v1alpha1",
        kind="PodNetworkConnectivityCheck",
    )
    ocp_utils.api.Route = MustGather(api_version="route.openshift.io/v1", kind="Route")
    ocp_utils.api.Secret = MustGather(api_version="v1", kind="Secret")
    ocp_utils.api.ServiceAccount = MustGather(api_version="v1", kind="ServiceAccount")
    ocp_utils.api.Subscription = MustGather(
        api_version="operators.coreos.com/v1alpha1", kind="Subscription"
    )

    ocp_utils.api.PerformanceProfile = MustGather(
        api_version="performance.openshift.io/v2", kind="PerformanceProfile"
    )
    ocp_utils.api.SriovNetworkNodeState = MustGather(
        api_version="sriovnetwork.openshift.io/v1", kind="SriovNetworkNodeState"
    )

    ocp_utils.api.ReadPodLogs = ocp_utils.mustgather.read_namespaced_pod_log
    ocp_utils.api.GetAlerts = ocp_utils.mustgather.get_alerts
    ocp_utils.api.GetCurrentTime = ocp_utils.mustgather.get_time


def has_oc_debug_access() -> bool:
    oc_debug_access = subprocess.run(  # nosec
        [
            "oc",
            "auth",
            "can-i",
            "create",
            "pods",
            "-n",
            "default",
        ],
        capture_output=True,
    )
    if oc_debug_access.returncode != 0:
        return False
    else:
        return True


def init_api(args: argparse.Namespace, k8s_config: client.Configuration) -> None:
    dynamic_client = dynamic.DynamicClient(
        client.api_client.ApiClient(configuration=k8s_config)
    )
    ocp_utils.api.CertificateSigningRequest = dynamic_client.resources.get(
        api_version="certificates.k8s.io/v1", kind="CertificateSigningRequest"
    )
    ocp_utils.api.ClusterOperator = dynamic_client.resources.get(
        api_version="config.openshift.io/v1", kind="ClusterOperator"
    )
    ocp_utils.api.ClusterServiceVersion = dynamic_client.resources.get(
        api_version="operators.coreos.com/v1alpha1", kind="ClusterServiceVersion"
    )
    ocp_utils.api.ClusterVersion = dynamic_client.resources.get(
        api_version="config.openshift.io/v1", kind="ClusterVersion"
    )
    ocp_utils.api.CustomResourceDefinition = dynamic_client.resources.get(
        api_version="apiextensions.k8s.io/v1", kind="CustomResourceDefinition"
    )
    ocp_utils.api.DNS = dynamic_client.resources.get(
        api_version="config.openshift.io/v1", kind="DNS"
    )
    ocp_utils.api.Event = dynamic_client.resources.get(api_version="v1", kind="Event")
    ocp_utils.api.KubeletConfig = dynamic_client.resources.get(
        api_version="machineconfiguration.openshift.io/v1", kind="KubeletConfig"
    )
    ocp_utils.api.MachineConfigPool = dynamic_client.resources.get(
        api_version="machineconfiguration.openshift.io/v1", kind="MachineConfigPool"
    )
    ocp_utils.api.Namespace = dynamic_client.resources.get(
        api_version="v1", kind="Namespace"
    )
    ocp_utils.api.Network = dynamic_client.resources.get(
        api_version="config.openshift.io/v1", kind="Network"
    )
    ocp_utils.api.Node = dynamic_client.resources.get(api_version="v1", kind="Node")
    ocp_utils.api.PersistentVolumeClaim = dynamic_client.resources.get(
        api_version="v1", kind="PersistentVolumeClaim"
    )
    ocp_utils.api.Pod = dynamic_client.resources.get(api_version="v1", kind="Pod")
    ocp_utils.api.PodNetworkConnectivityCheck = dynamic_client.resources.get(
        api_version="controlplane.operator.openshift.io/v1alpha1",
        kind="PodNetworkConnectivityCheck",
    )
    ocp_utils.api.Route = dynamic_client.resources.get(
        api_version="route.openshift.io/v1", kind="Route"
    )
    ocp_utils.api.Secret = dynamic_client.resources.get(api_version="v1", kind="Secret")
    ocp_utils.api.ServiceAccount = dynamic_client.resources.get(
        api_version="v1", kind="ServiceAccount"
    )
    ocp_utils.api.Subscription = dynamic_client.resources.get(
        api_version="operators.coreos.com/v1alpha1", kind="Subscription"
    )
    # Not every cluster supports the following resource types
    try:
        ocp_utils.api.PerformanceProfile = dynamic_client.resources.get(
            api_version="performance.openshift.io/v2", kind="PerformanceProfile"
        )
        ocp_utils.api.SriovNetworkNodeState = dynamic_client.resources.get(
            api_version="sriovnetwork.openshift.io/v1", kind="SriovNetworkNodeState"
        )
    except dynamic.exceptions.ResourceNotFoundError:
        pass
    ocp_utils.api.ReadPodLogs = read_namespaced_pod_log
    ocp_utils.api.GetAlerts = get_alerts
    ocp_utils.api.GetCurrentTime = get_time
    bearer_token = (
        dynamic_client.configuration.auth_settings()
        .get("BearerToken", {})
        .get("value", "")
    )
    _prom_init(bearer_token)

    if args.skip_oc_debug is False:
        if has_oc_debug_access() is False:
            args.skip_oc_debug = True
