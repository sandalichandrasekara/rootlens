#!/usr/bin/env python3
"""
Scheduling Sub-Cause Data Collection

Collects real data for training the Scheduling sub-cause explainer model.
Each experiment triggers a specific scheduling delay sub-cause.

Sub-causes:
1. taint_conflict - Pod tolerations don't match node taints
2. resource_quota_exceeded - Namespace quota limits hit
3. node_affinity_mismatch - No nodes match affinity rules
4. pdb_violation - PodDisruptionBudget blocking scheduling
5. insufficient_resources - No nodes with enough CPU/memory

Usage:
    python3 run_scheduling_subcause_experiments.py

Prerequisites:
    - Minikube running
    - kubectl configured
    - Python packages: pyyaml
"""

import subprocess
import json
import time
import yaml
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('scheduling_subcause_experiments.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Output directory
DATA_DIR = Path(__file__).parent / "raw_data" / "scheduling_subcauses"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Namespace for experiments
NAMESPACE = "scheduling-test"


class KubernetesClient:
    """Helper for Kubernetes operations"""

    def run_kubectl(self, args: str, timeout: int = 30) -> Tuple[bool, str]:
        """Run kubectl command and return (success, output)"""
        try:
            result = subprocess.run(
                f"kubectl {args}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def apply_yaml(self, manifest: dict) -> bool:
        """Apply a YAML manifest"""
        yaml_str = yaml.dump(manifest)
        result = subprocess.run(
            "kubectl apply -f -",
            shell=True,
            input=yaml_str,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"Apply failed: {result.stderr}")
        return result.returncode == 0

    def apply_yaml_with_error(self, manifest: dict) -> Tuple[bool, str]:
        """Apply a YAML manifest and return (success, error_message)"""
        yaml_str = yaml.dump(manifest)
        result = subprocess.run(
            "kubectl apply -f -",
            shell=True,
            input=yaml_str,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stderr

    def delete_resource(self, kind: str, name: str, namespace: str = NAMESPACE) -> bool:
        """Delete a Kubernetes resource"""
        success, _ = self.run_kubectl(
            f"delete {kind} {name} -n {namespace} --ignore-not-found"
        )
        return success

    def get_node_info(self) -> Dict:
        """Get cluster node information"""
        success, output = self.run_kubectl("get nodes -o json")
        if not success:
            return {"count": 1, "available_cpu": 2000}

        try:
            data = json.loads(output)
            nodes = data.get("items", [])

            total_cpu = 0
            for node in nodes:
                # Get allocatable CPU
                allocatable = node.get("status", {}).get("allocatable", {})
                cpu = allocatable.get("cpu", "2")
                # Convert to millicores
                if cpu.endswith("m"):
                    total_cpu += int(cpu[:-1])
                else:
                    total_cpu += int(cpu) * 1000

            return {
                "count": len(nodes),
                "available_cpu_millicores": total_cpu,
            }
        except:
            return {"count": 1, "available_cpu_millicores": 2000}

    def wait_for_pod_scheduling(self, name: str, namespace: str = NAMESPACE,
                                 timeout: int = 60) -> Dict:
        """
        Wait for pod to be scheduled (or fail scheduling) and collect metrics.

        Returns scheduling metrics including duration, failure reason, etc.
        """
        start_time = time.time()
        scheduling_attempts = 0
        last_failure_reason = ""
        scheduled = False

        while time.time() - start_time < timeout:
            success, output = self.run_kubectl(
                f"get pod {name} -n {namespace} -o json"
            )

            if not success:
                time.sleep(1)
                continue

            try:
                pod = json.loads(output)
                status = pod.get("status", {})
                phase = status.get("phase", "")
                conditions = status.get("conditions", [])

                # Check if scheduled
                for condition in conditions:
                    if condition.get("type") == "PodScheduled":
                        if condition.get("status") == "True":
                            scheduled = True
                            break
                        elif condition.get("status") == "False":
                            scheduling_attempts += 1
                            last_failure_reason = condition.get("reason", "")
                           
                            message = condition.get("message", "")
                            if "Insufficient" in message:
                                last_failure_reason = "InsufficientResources"
                            elif "taint" in message.lower():
                                last_failure_reason = "TaintToleration"
                            elif "affinity" in message.lower():
                                last_failure_reason = "NodeAffinityMismatch"
                            elif "quota" in message.lower():
                                last_failure_reason = "ResourceQuotaExceeded"

                if scheduled or phase in ["Running", "Succeeded", "Failed"]:
                    break

            except json.JSONDecodeError:
                pass

            time.sleep(1)

        scheduling_duration = time.time() - start_time

        return {
            "scheduling_duration_seconds": scheduling_duration,
            "scheduling_attempts": max(scheduling_attempts, 1),
            "scheduled": scheduled,
            "scheduling_failure_reason": last_failure_reason,
        }

    def get_pod_events(self, name: str, namespace: str = NAMESPACE) -> List[Dict]:
        """Get events for a pod"""
        success, output = self.run_kubectl(
            f"get events -n {namespace} --field-selector involvedObject.name={name} -o json"
        )

        if not success:
            return []

        try:
            events_data = json.loads(output)
            events = []
            for item in events_data.get("items", []):
                events.append({
                    "reason": item.get("reason"),
                    "message": item.get("message"),
                    "type": item.get("type"),
                    "count": item.get("count", 1),
                })
            return events
        except json.JSONDecodeError:
            return []


class SchedulingSubcauseExperiments:
    """Run experiments for each scheduling sub-cause"""

    def __init__(self):
        self.k8s = KubernetesClient()

    def setup_namespace(self):
        """Create test namespace"""
        logger.info(f"Setting up namespace: {NAMESPACE}")
        manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": NAMESPACE}
        }
        self.k8s.apply_yaml(manifest)
        time.sleep(2)

    def cleanup_namespace(self):
        """Clean up test namespace"""
        logger.info(f"Cleaning up namespace: {NAMESPACE}")
        self.k8s.run_kubectl(f"delete namespace {NAMESPACE} --ignore-not-found")
        time.sleep(5)

    def cleanup_pods(self):
        """Clean up all test pods"""
        self.k8s.run_kubectl(f"delete pods -n {NAMESPACE} --all --ignore-not-found")
        time.sleep(3)

    def run_single_experiment(self, pod_manifest: dict, sub_cause: str,
                               description: str, extra_metrics: dict = None,
                               setup_func=None, teardown_func=None,
                               wait_timeout: int = 60) -> Optional[Dict]:
        """
        Run a single scheduling experiment.
        """
        pod_name = pod_manifest["metadata"]["name"]

        logger.info(f"  Deploying pod: {pod_name}")

        # Run setup if provided
        if setup_func:
            setup_func()
            time.sleep(2)

        # Clean up any existing pod
        self.k8s.delete_resource("pod", pod_name)
        time.sleep(2)

        # Get node info
        node_info = self.k8s.get_node_info()

        # Deploy the pod - capture error for admission rejections
        deploy_start = time.time()
        deploy_success, deploy_error = self.k8s.apply_yaml_with_error(pod_manifest)

        # Check if this is an admission rejection 
        admission_rejection = False
        rejection_reason = ""
        if not deploy_success:
            error_lower = deploy_error.lower()
            if "exceeded quota" in error_lower or "forbidden" in error_lower:
                admission_rejection = True
                rejection_reason = "ResourceQuotaExceeded"
                logger.info(f"   Quota rejection triggered (expected for resource_quota_exceeded)")
            elif "admission" in error_lower:
                admission_rejection = True
                rejection_reason = "AdmissionRejected"
                logger.info(f"   Admission rejection triggered")
            else:
                logger.error(f"  Failed to deploy pod: {deploy_error}")
                if teardown_func:
                    teardown_func()
                return None

        # If admission rejected, create sample directly from the rejection
        if admission_rejection:
            spec = pod_manifest.get("spec", {})
            containers = spec.get("containers", [{}])
            main_container = containers[0] if containers else {}
            resources = main_container.get("resources", {})
            requests = resources.get("requests", {})

            # Parse CPU request
            cpu_request = requests.get("cpu", "100m")
            if cpu_request.endswith("m"):
                cpu_millicores = int(cpu_request[:-1])
            else:
                cpu_millicores = int(cpu_request) * 1000

            # Parse memory request
            mem_request = requests.get("memory", "128Mi")
            if mem_request.endswith("Mi"):
                mem_mb = int(mem_request[:-2])
            elif mem_request.endswith("Gi"):
                mem_mb = int(mem_request[:-2]) * 1024
            else:
                mem_mb = 128

            sample = {
                "timestamp": datetime.now().isoformat(),
                "sub_cause": sub_cause,
                "description": description,
                "pod_name": pod_name,
                "scheduling_duration_seconds": time.time() - deploy_start,
                "scheduling_attempts": 1,
                "scheduled": False,
                "scheduling_failure_reason": rejection_reason,
                "admission_rejected": True,
                "has_node_selector": 1.0 if spec.get("nodeSelector") else 0.0,
                "has_node_affinity": 1.0 if spec.get("affinity", {}).get("nodeAffinity") else 0.0,
                "has_tolerations": 1.0 if spec.get("tolerations") else 0.0,
                "pod_priority": spec.get("priority", 0),
                "cpu_request_millicores": cpu_millicores,
                "memory_request_mb": mem_mb,
                "node_count_in_cluster": node_info["count"],
                "available_cpu_millicores": node_info["available_cpu_millicores"],
                "resource_pressure_score": cpu_millicores / max(node_info["available_cpu_millicores"], 1),
                "events": [],
                "error_message": deploy_error,
            }

            if extra_metrics:
                sample.update(extra_metrics)

            if teardown_func:
                teardown_func()

            logger.info(f"   Collected admission rejection sample: {rejection_reason}")
            return sample

        # Normal flow - pod was created, wait for scheduling
        logger.info(f"  Waiting for scheduling result...")
        scheduling_metrics = self.k8s.wait_for_pod_scheduling(
            pod_name, timeout=wait_timeout
        )

        # Get events
        events = self.k8s.get_pod_events(pod_name)

        # Extract pod spec info
        spec = pod_manifest.get("spec", {})
        containers = spec.get("containers", [{}])
        main_container = containers[0] if containers else {}
        resources = main_container.get("resources", {})
        requests = resources.get("requests", {})

        # Parse CPU request
        cpu_request = requests.get("cpu", "100m")
        if cpu_request.endswith("m"):
            cpu_millicores = int(cpu_request[:-1])
        else:
            cpu_millicores = int(cpu_request) * 1000

        # Parse memory request
        mem_request = requests.get("memory", "128Mi")
        if mem_request.endswith("Mi"):
            mem_mb = int(mem_request[:-2])
        elif mem_request.endswith("Gi"):
            mem_mb = int(mem_request[:-2]) * 1024
        else:
            mem_mb = 128

        # Build sample
        sample = {
            "timestamp": datetime.now().isoformat(),
            "sub_cause": sub_cause,
            "description": description,
            "pod_name": pod_name,
            **scheduling_metrics,
            "has_node_selector": 1.0 if spec.get("nodeSelector") else 0.0,
            "has_node_affinity": 1.0 if spec.get("affinity", {}).get("nodeAffinity") else 0.0,
            "has_tolerations": 1.0 if spec.get("tolerations") else 0.0,
            "pod_priority": spec.get("priority", 0),
            "cpu_request_millicores": cpu_millicores,
            "memory_request_mb": mem_mb,
            "node_count_in_cluster": node_info["count"],
            "available_cpu_millicores": node_info["available_cpu_millicores"],
            "events": events,
        }

        # Add extra metrics
        if extra_metrics:
            sample.update(extra_metrics)

        # Calculate resource pressure score
        if node_info["available_cpu_millicores"] > 0:
            sample["resource_pressure_score"] = (
                cpu_millicores / node_info["available_cpu_millicores"]
            )
        else:
            sample["resource_pressure_score"] = 1.0

        # Cleanup
        self.k8s.delete_resource("pod", pod_name)
        if teardown_func:
            teardown_func()

        status = "scheduled" if scheduling_metrics["scheduled"] else "failed"
        logger.info(f"   Collected sample: {status}, "
                   f"duration={scheduling_metrics['scheduling_duration_seconds']:.2f}s, "
                   f"reason={scheduling_metrics['scheduling_failure_reason']}")

        return sample

    # SUB-CAUSE 1: TAINT CONFLICT

    def run_taint_conflict_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Trigger taint conflicts by adding taints to nodes that pods don't tolerate.
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: taint_conflict")
        logger.info("=" * 80)

        samples = []

        # Taint configurations
        taint_configs = [
            {"key": "experiment", "value": "scheduling", "effect": "NoSchedule"},
            {"key": "dedicated", "value": "test", "effect": "NoSchedule"},
            {"key": "special", "value": "true", "effect": "NoExecute"},
        ]

        def add_taint(config):
            """Add taint to minikube node"""
            taint_str = f"{config['key']}={config['value']}:{config['effect']}"
            self.k8s.run_kubectl(f"taint nodes minikube {taint_str} --overwrite")

        def remove_taint(config):
            """Remove taint from minikube node"""
            taint_str = f"{config['key']}={config['value']}:{config['effect']}-"
            self.k8s.run_kubectl(f"taint nodes minikube {taint_str}")

        for i in range(num_samples):
            config = taint_configs[i % len(taint_configs)]

            logger.info(f"\nSample {i+1}/{num_samples}: taint_conflict "
                       f"({config['key']}={config['value']}:{config['effect']})")

            # Create pod WITHOUT matching toleration
            pod_manifest = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": f"taint-test-{i}",
                    "namespace": NAMESPACE,
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "main",
                        "image": "busybox:latest",
                        "command": ["sleep", "60"],
                        "resources": {
                            "requests": {"cpu": "50m", "memory": "64Mi"}
                        }
                    }],

                }
            }

            sample = self.run_single_experiment(
                pod_manifest=pod_manifest,
                sub_cause="taint_conflict",
                description=f"Taint conflict: {config['key']}={config['value']}",
                extra_metrics={
                    "taint_key": config["key"],
                    "taint_effect": config["effect"],
                },
                setup_func=lambda c=config: add_taint(c),
                teardown_func=lambda c=config: remove_taint(c),
                wait_timeout=30,  
            )

            if sample:
                samples.append(sample)

            time.sleep(3)

        logger.info(f"\n Collected {len(samples)} taint_conflict samples")
        return samples

    # SUB-CAUSE 2: RESOURCE QUOTA EXCEEDED

    def run_resource_quota_exceeded_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Trigger resource quota exceeded by setting tight quota limits.
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: resource_quota_exceeded")
        logger.info("=" * 80)

        samples = []

        # Quota configurations 
        quota_configs = [
            {"cpu": "100m", "memory": "64Mi", "pods": "1"},
            {"cpu": "50m", "memory": "32Mi", "pods": "1"},
            {"cpu": "200m", "memory": "128Mi", "pods": "0"},  
        ]

        def create_quota(config):
            """Create ResourceQuota"""
            quota = {
                "apiVersion": "v1",
                "kind": "ResourceQuota",
                "metadata": {
                    "name": "test-quota",
                    "namespace": NAMESPACE,
                },
                "spec": {
                    "hard": {
                        "requests.cpu": config["cpu"],
                        "requests.memory": config["memory"],
                        "pods": config["pods"],
                    }
                }
            }
            self.k8s.apply_yaml(quota)

        def delete_quota():
            """Delete ResourceQuota"""
            self.k8s.delete_resource("resourcequota", "test-quota")

        for i in range(num_samples):
            config = quota_configs[i % len(quota_configs)]

            logger.info(f"\nSample {i+1}/{num_samples}: resource_quota_exceeded "
                       f"(cpu={config['cpu']}, mem={config['memory']}, pods={config['pods']})")

            # Pod requesting more than quota allows
            pod_manifest = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": f"quota-test-{i}",
                    "namespace": NAMESPACE,
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "main",
                        "image": "busybox:latest",
                        "command": ["sleep", "60"],
                        "resources": {
                            "requests": {
                                "cpu": "500m",  
                                "memory": "256Mi"
                            }
                        }
                    }]
                }
            }

            sample = self.run_single_experiment(
                pod_manifest=pod_manifest,
                sub_cause="resource_quota_exceeded",
                description=f"Quota exceeded: cpu={config['cpu']}, pods={config['pods']}",
                extra_metrics={
                    "quota_cpu": config["cpu"],
                    "quota_memory": config["memory"],
                    "quota_pods": config["pods"],
                },
                setup_func=lambda c=config: create_quota(c),
                teardown_func=delete_quota,
                wait_timeout=20,
            )

            if sample:
                samples.append(sample)

            time.sleep(3)

        logger.info(f"\n Collected {len(samples)} resource_quota_exceeded samples")
        return samples

    # SUB-CAUSE 3: NODE AFFINITY MISMATCH

    def run_node_affinity_mismatch_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Trigger node affinity mismatch by requiring non-existent node labels.
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: node_affinity_mismatch")
        logger.info("=" * 80)

        samples = []

        # Non-existent labels to require
        affinity_configs = [
            {"key": "zone", "value": "non-existent-zone"},
            {"key": "gpu", "value": "true"},
            {"key": "special-hardware", "value": "quantum"},
            {"key": "region", "value": "mars-west-1"},
        ]

        for i in range(num_samples):
            config = affinity_configs[i % len(affinity_configs)]

            logger.info(f"\nSample {i+1}/{num_samples}: node_affinity_mismatch "
                       f"({config['key']}={config['value']})")

            # Pod with required node affinity for non-existent label
            pod_manifest = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": f"affinity-test-{i}",
                    "namespace": NAMESPACE,
                },
                "spec": {
                    "restartPolicy": "Never",
                    "affinity": {
                        "nodeAffinity": {
                            "requiredDuringSchedulingIgnoredDuringExecution": {
                                "nodeSelectorTerms": [{
                                    "matchExpressions": [{
                                        "key": config["key"],
                                        "operator": "In",
                                        "values": [config["value"]]
                                    }]
                                }]
                            }
                        }
                    },
                    "containers": [{
                        "name": "main",
                        "image": "busybox:latest",
                        "command": ["sleep", "60"],
                        "resources": {
                            "requests": {"cpu": "50m", "memory": "64Mi"}
                        }
                    }]
                }
            }

            sample = self.run_single_experiment(
                pod_manifest=pod_manifest,
                sub_cause="node_affinity_mismatch",
                description=f"Affinity mismatch: {config['key']}={config['value']}",
                extra_metrics={
                    "affinity_key": config["key"],
                    "affinity_value": config["value"],
                },
                wait_timeout=30,
            )

            if sample:
                samples.append(sample)

            time.sleep(3)

        logger.info(f"\n Collected {len(samples)} node_affinity_mismatch samples")
        return samples

    # SUB-CAUSE 4: PDB VIOLATION

    def run_pdb_violation_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Trigger PDB violation by creating PDB that blocks scheduling.

        Note: PDB typically affects eviction, not initial scheduling.
        We simulate this by creating scenarios where PDB awareness affects scheduling.
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: pdb_violation")
        logger.info("=" * 80)

        samples = []


        def create_deployment_and_pdb():
            """Create a deployment with PDB"""
            # Create deployment
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "pdb-target",
                    "namespace": NAMESPACE,
                },
                "spec": {
                    "replicas": 2,
                    "selector": {"matchLabels": {"app": "pdb-target"}},
                    "template": {
                        "metadata": {"labels": {"app": "pdb-target"}},
                        "spec": {
                            "containers": [{
                                "name": "main",
                                "image": "busybox:latest",
                                "command": ["sleep", "300"],
                                "resources": {
                                    "requests": {"cpu": "100m", "memory": "64Mi"}
                                }
                            }]
                        }
                    }
                }
            }
            self.k8s.apply_yaml(deployment)

            # Create restrictive PDB
            pdb = {
                "apiVersion": "policy/v1",
                "kind": "PodDisruptionBudget",
                "metadata": {
                    "name": "pdb-test",
                    "namespace": NAMESPACE,
                },
                "spec": {
                    "minAvailable": 2,  # All pods must be available
                    "selector": {"matchLabels": {"app": "pdb-target"}}
                }
            }
            self.k8s.apply_yaml(pdb)
            time.sleep(10)  # Wait for deployment

        def delete_deployment_and_pdb():
            """Clean up deployment and PDB"""
            self.k8s.delete_resource("pdb", "pdb-test")
            self.k8s.delete_resource("deployment", "pdb-target")

        for i in range(num_samples):
            logger.info(f"\nSample {i+1}/{num_samples}: pdb_violation")

            # Create PDB scenario
            create_deployment_and_pdb()

            # Pod that would be affected by PDB (same selector)
            pod_manifest = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": f"pdb-test-{i}",
                    "namespace": NAMESPACE,
                    "labels": {"app": "pdb-target"},  
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "main",
                        "image": "busybox:latest",
                        "command": ["sleep", "60"],
                        "resources": {
                            "requests": {"cpu": "50m", "memory": "64Mi"}
                        }
                    }]
                }
            }

            sample = self.run_single_experiment(
                pod_manifest=pod_manifest,
                sub_cause="pdb_violation",
                description="PDB with minAvailable=2",
                extra_metrics={
                    "pdb_min_available": 2,
                },
                teardown_func=delete_deployment_and_pdb,
                wait_timeout=30,
            )

            if sample:
                samples.append(sample)

            time.sleep(5)

        logger.info(f"\n Collected {len(samples)} pdb_violation samples")
        return samples

    # SUB-CAUSE 5: INSUFFICIENT RESOURCES

    def run_insufficient_resources_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Trigger insufficient resources by requesting more than available.
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: insufficient_resources")
        logger.info("=" * 80)

        samples = []

        # Resource configurations that exceed typical Minikube capacity
        resource_configs = [
            {"cpu": "16000m", "memory": "32Gi"},   # Huge CPU
            {"cpu": "8000m", "memory": "64Gi"},    # Huge memory
            {"cpu": "32000m", "memory": "16Gi"},   # Both excessive
            {"cpu": "100000m", "memory": "8Gi"},   # Extreme CPU
        ]

        for i in range(num_samples):
            config = resource_configs[i % len(resource_configs)]

            logger.info(f"\nSample {i+1}/{num_samples}: insufficient_resources "
                       f"(cpu={config['cpu']}, memory={config['memory']})")

            # Pod requesting excessive resources
            pod_manifest = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": f"resource-test-{i}",
                    "namespace": NAMESPACE,
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "main",
                        "image": "busybox:latest",
                        "command": ["sleep", "60"],
                        "resources": {
                            "requests": {
                                "cpu": config["cpu"],
                                "memory": config["memory"]
                            }
                        }
                    }]
                }
            }

            sample = self.run_single_experiment(
                pod_manifest=pod_manifest,
                sub_cause="insufficient_resources",
                description=f"Excessive resources: {config['cpu']}, {config['memory']}",
                extra_metrics={
                    "requested_cpu": config["cpu"],
                    "requested_memory": config["memory"],
                },
                wait_timeout=30,
            )

            if sample:
                samples.append(sample)

            time.sleep(3)

        logger.info(f"\n Collected {len(samples)} insufficient_resources samples")
        return samples

    # MAIN METHODS

    def save_samples(self, samples: List[Dict], sub_cause: str):
        """Save samples to JSON file"""
        if not samples:
            logger.warning(f"No samples to save for {sub_cause}")
            return

        filename = DATA_DIR / f"{sub_cause}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, 'w') as f:
            json.dump(samples, f, indent=2, default=str)

        logger.info(f" Saved {len(samples)} samples to {filename}")

    def run_all_experiments(self, samples_per_subcause: int = 10):
        """Run all scheduling sub-cause experiments"""
        logger.info("\n" + "=" * 80)
        logger.info("SCHEDULING SUB-CAUSE DATA COLLECTION")
        logger.info("=" * 80 + "\n")

        self.setup_namespace()

        all_samples = {}

        # 1. Taint Conflict
        samples = self.run_taint_conflict_experiments(samples_per_subcause)
        all_samples["taint_conflict"] = samples
        self.save_samples(samples, "taint_conflict")
        self.cleanup_pods()
        time.sleep(5)

        # 2. Resource Quota Exceeded
        samples = self.run_resource_quota_exceeded_experiments(samples_per_subcause)
        all_samples["resource_quota_exceeded"] = samples
        self.save_samples(samples, "resource_quota_exceeded")
        self.cleanup_pods()
        time.sleep(5)

        # 3. Node Affinity Mismatch
        samples = self.run_node_affinity_mismatch_experiments(samples_per_subcause)
        all_samples["node_affinity_mismatch"] = samples
        self.save_samples(samples, "node_affinity_mismatch")
        self.cleanup_pods()
        time.sleep(5)

        # 4. PDB Violation
        samples = self.run_pdb_violation_experiments(samples_per_subcause)
        all_samples["pdb_violation"] = samples
        self.save_samples(samples, "pdb_violation")
        self.cleanup_pods()
        time.sleep(5)

        # 5. Insufficient Resources
        samples = self.run_insufficient_resources_experiments(samples_per_subcause)
        all_samples["insufficient_resources"] = samples
        self.save_samples(samples, "insufficient_resources")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("COLLECTION SUMMARY")
        logger.info("=" * 80)

        total = 0
        for sub_cause, samples in all_samples.items():
            count = len(samples)
            total += count
            logger.info(f"  {sub_cause}: {count} samples")

        logger.info(f"\nTotal: {total} samples")
        logger.info(f"Saved to: {DATA_DIR}")

        # Cleanup
        self.cleanup_namespace()

        return all_samples


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Collect scheduling sub-cause data")
    parser.add_argument(
        "--samples", "-n",
        type=int,
        default=10,
        help="Number of samples per sub-cause (default: 10)"
    )
    parser.add_argument(
        "--subcause", "-s",
        choices=["taint_conflict", "resource_quota_exceeded", "node_affinity_mismatch",
                 "pdb_violation", "insufficient_resources", "all"],
        default="all",
        help="Which sub-cause to collect data for (default: all)"
    )

    args = parser.parse_args()

    experiments = SchedulingSubcauseExperiments()

    if args.subcause == "all":
        experiments.run_all_experiments(args.samples)
    else:
        experiments.setup_namespace()

        if args.subcause == "taint_conflict":
            samples = experiments.run_taint_conflict_experiments(args.samples)
        elif args.subcause == "resource_quota_exceeded":
            samples = experiments.run_resource_quota_exceeded_experiments(args.samples)
        elif args.subcause == "node_affinity_mismatch":
            samples = experiments.run_node_affinity_mismatch_experiments(args.samples)
        elif args.subcause == "pdb_violation":
            samples = experiments.run_pdb_violation_experiments(args.samples)
        elif args.subcause == "insufficient_resources":
            samples = experiments.run_insufficient_resources_experiments(args.samples)

        experiments.save_samples(samples, args.subcause)
        experiments.cleanup_namespace()


if __name__ == "__main__":
    main()
