from datetime import datetime
from typing import List, Dict, Any
import os
import concurrent.futures
import yaml
import argparse
import json
import dateutil.parser

mg_resources: List[Dict[str, Any]] = []
mg_alerts: List[Dict[str, Any]] = []
mg_path: str = ""


def load_yaml(path: str, args: argparse.Namespace) -> Any:
    with open(path, "r") as resource:
        try:
            return yaml.safe_load(resource)
        except (
            yaml.constructor.ConstructorError,
            yaml.scanner.ScannerError,
            yaml.parser.ParserError,
        ):
            if not args.results_only:
                print(f"Could not parse: {path}")
            return None


def get_root_dir() -> str:
    try:
        return os.path.join(
            mg_path,
            next(
                item
                for item in os.listdir(mg_path)
                if item.startswith("quay-io-openshift-release")
            ),
        )
    except StopIteration:
        return mg_path


def get_time() -> datetime:
    with open(os.path.join(get_root_dir(), "timestamp"), "r") as f:
        return dateutil.parser.parse(f.readline().rsplit(" ", 2)[0])


# This function unpacks lists and imports resources one by one
def recurse_output(output: Dict[str, Any]) -> None:
    if output["kind"].endswith("List"):
        if output.get("items"):
            for item in output["items"]:
                recurse_output(item)
    else:
        found = False
        for resource in mg_resources:
            if (
                output["kind"] == resource["kind"]
                and output["apiVersion"] == resource["apiVersion"]
                and output["metadata"].get("namespace")
                == resource["metadata"].get("namespace")
                and output["metadata"]["name"] == resource["metadata"]["name"]
            ):
                found = True
        if found is False:
            mg_resources.append(output)
        return


def read_must_gather(args: argparse.Namespace) -> None:
    # YAML files are read in multiple processes
    with concurrent.futures.ProcessPoolExecutor() as executor:
        tasks = []
        for root, dirs, files in os.walk(mg_path):
            for name in files:
                if name.endswith(".yaml"):
                    tasks.append(
                        executor.submit(load_yaml, os.path.join(root, name), args)
                    )
        for task in concurrent.futures.as_completed(tasks):
            output = task.result()
            if output:
                recurse_output(output)

    alerts_paths = [
        os.path.join(get_root_dir(), "monitoring/prometheus/rules.json"),
        os.path.join(get_root_dir(), "monitoring/alerts.json"),
    ]
    for path in alerts_paths:
        try:
            with open(path, "r") as resource:
                mg_alerts.extend(json.load(resource)["data"]["groups"])
            break
        except (FileNotFoundError, json.JSONDecodeError):
            pass


def read_namespaced_pod_log(namespace: str, name: str, container: str) -> str:
    with open(
        os.path.join(
            get_root_dir(),
            f"namespaces/{namespace}/pods/{name}/{container}/{container}/logs/current.log",
        ),
        "r",
    ) as log:
        return log.read()


def get_alerts() -> List[Any]:
    firing_alerts = []
    for group in mg_alerts:
        for rule in group["rules"]:
            if rule.get("type") == "alerting" and rule.get("state") == "firing":
                firing_alerts.extend(rule["alerts"])
    return firing_alerts


class dotdict(Dict[str, Any]):
    """dot.notation access to dictionary attributes"""

    def __getattr__(*args: Any) -> Any:
        val = dict.get(*args)
        return dotdict(val) if type(val) is dict else val

    __setattr__: Any = dict.__setitem__
    __delattr__: Any = dict.__delitem__


class MustGather:
    def __init__(self, api_version: str, kind: str) -> None:
        self.api_kind = {"apiVersion": api_version, "kind": kind}

    # Very basic parser for field selectors
    def get_field_value(self, base: Dict[str, Any], field: str, labels: bool) -> Any:
        if field.startswith("!"):
            field = field[1:]
        field = field.split("!=")[0]
        field = field.split("=")[0]
        if labels is True:
            return base.get(field)
        dotted_base = dotdict(base)  # noqa: F841
        try:
            return eval(f"dotted_base.{field}")  # nosec
        except AttributeError:
            return None

    def parse_selector(
        self, selector: str, items: List[Dict[str, Any]], labels: bool
    ) -> None:
        selector = selector.replace("==", "=")
        for item in list(items):
            if labels:
                base = item["metadata"].get("labels", {})
            else:
                base = item
            for field in selector.split(","):
                parsed_field = self.get_field_value(base, field, labels)
                if field.startswith("!"):
                    if parsed_field is not None:
                        items.remove(item)
                elif "!=" in field:
                    if parsed_field == field.split("!=")[1]:
                        items.remove(item)
                elif "=" in field:
                    if parsed_field != field.split("=")[1]:
                        items.remove(item)

    def get(
        self, label_selector: str = "", field_selector: str = "", **kwargs: str
    ) -> Any:
        items: List[Dict[str, Any]] = []
        for resource in mg_resources:
            if (
                self.api_kind.items() <= resource.items()
                and kwargs.items() <= resource.get("metadata", {}).items()
            ):
                if resource not in items:
                    items.append(resource)

        if label_selector:
            self.parse_selector(label_selector, items, True)
        if field_selector:
            self.parse_selector(field_selector, items, False)
        if not kwargs.get("name"):
            return {"items": items}
        elif len(items) > 0:
            return items[0]
        else:
            raise ValueError
