# openshift-checks-py
Adapted from https://github.com/RHsyseng/openshift-checks

## Dependencies
### Python packages
```
pip install -r requirements.txt
```
### OpenShift client
```
curl -L -O https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable/openshift-client-linux.tar.gz
```
https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html#installing-openshift-cli

## Usage
```
usage: openshift-checks.py [-h] [-n] [-s SINGLE] [-l] [-r] [-p PARALLEL_JOBS] [-i] [--skip SKIP] [--skip-oc-debug] [-m MUST_GATHER] [--entropy-threshold ENTROPY_THRESHOLD] [--ovn-memory-threshold OVN_MEMORY_THRESHOLD]
                           [--port-thrasing-threshold PORT_THRASING_THRESHOLD] [--reserved-cpu-threshold RESERVED_CPU_THRESHOLD] [--zombie-threshold ZOMBIE_THRESHOLD] [--network-threshold NETWORK_THRESHOLD]
                           [--flap-threshold FLAP_THRESHOLD]

Perform a health check on an OpenShift cluster.

options:
  -h, --help            show this help message and exit
  -n, --no-colors       Disable colored output
  -s SINGLE, --single SINGLE
                        Run a single check
  -l, --list            List checks
  -r, --results-only    Only show results
  -p PARALLEL_JOBS, --parallel-jobs PARALLEL_JOBS
                        How many oc debug jobs to run in parallel. Default=3
  -i, --incluster-config
                        Use in-cluster config
  --skip SKIP           Comma separated list of checks to skip
  --skip-oc-debug       Skip checks that use oc debug
  -m MUST_GATHER, --must-gather MUST_GATHER
                        Path to a must-gather folder
  --entropy-threshold ENTROPY_THRESHOLD
                        Entropy threshold in bits. Default=200
  --ovn-memory-threshold OVN_MEMORY_THRESHOLD
                        OVN pod memory threshold in Mi. Default=5000
  --port-thrasing-threshold PORT_THRASING_THRESHOLD
                        OVN port thrasing message threshold. Default=10
  --reserved-cpu-threshold RESERVED_CPU_THRESHOLD
                        Reserved CPU usage threshold in percent. Default=80
  --zombie-threshold ZOMBIE_THRESHOLD
                        Zombie process count threshold. Default=5
  --network-threshold NETWORK_THRESHOLD
                        Network error/drop threshold in percent. Default=1
  --flap-threshold FLAP_THRESHOLD
                        Interface flapping threshold. Default=5
```

## must-gather
A must-gather is an offline support bundle. It contains resource definitions and logs. See https://docs.openshift.com/container-platform/latest/support/gathering-cluster-data.html#support_gathering_data_gathering-cluster-data

This tool can run a health check against a must-gather. Some checks will be skipped (checks that require "oc debug" access, and checks that require live network access).

```
openshift-checks.py -m <path_to_must_gather_folder>
```
Initialization can take a while when running against a must-gather, it needs to read all the YAML resource definitions into memory.
## Container
```
podman run --pull always -it --rm -v $HOME/.kube/config:/kubeconfig:Z quay.io/loganmc10/openshift-checks-py:latest -h
```

## Linux Binary
```
curl -L https://github.com/loganmc10/openshift-checks-py/releases/latest/download/openshift-checks -o openshift-checks
chmod +x ./openshift-checks
```

It is built using PyInstaller, so it is portable and doesn't have dependencies (except the oc binary).

## CronJob
Creates a daily CronJob on an OpenShift cluster. Job will fail if any of the checks fail.
```
oc apply -f cronjob.yaml
```
Run manually:
```
oc create job -n checks-openshift --from=cronjob/openshift-checks-py check
```
