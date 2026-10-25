#!/usr/bin/env python3
"""
Cold Start Sub-Cause Data Collection

Collects real data for training the Cold Start sub-cause explainer model.
Each experiment triggers a specific sub-cause and collects metrics.

Sub-causes:
1. image_pull_latency - Large image or cache miss causes slow pull
2. init_container_delay - Slow init containers delay pod readiness
3. readiness_probe_failure - Probe failures delay pod becoming ready
4. container_runtime_slow - Container creation takes too long
5. registry_timeout - Registry connectivity issues cause pull errors

Usage:
    python3 run_cold_start_subcause_experiments.py

Prerequisites:
    - Minikube running with KEDA and RabbitMQ
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
        logging.FileHandler('cold_start_subcause_experiments.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Output directory
DATA_DIR = Path(__file__).parent / "raw_data" / "cold_start_subcauses"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Namespace for experiments
NAMESPACE = "default"

# Base pod template
BASE_POD_TEMPLATE = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "name": "cold-start-test",
        "namespace": NAMESPACE,
        "labels": {
            "app": "cold-start-experiment",
            "experiment": "subcause"
        }
    },
    "spec": {
        "restartPolicy": "Never",
        "containers": [{
            "name": "main",
            "image": "busybox:latest",
            "command": ["sh", "-c", "echo ready && sleep 300"],
            "resources": {
                "requests": {"cpu": "50m", "memory": "64Mi"},
                "limits": {"cpu": "100m", "memory": "128Mi"}
            }
        }]
    }
}


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
        return result.returncode == 0

    def delete_pod(self, name: str, namespace: str = NAMESPACE) -> bool:
        """Delete a pod"""
        success, _ = self.run_kubectl(f"delete pod {name} -n {namespace} --ignore-not-found")
        return success

    def wait_for_pod(self, name: str, namespace: str = NAMESPACE,
                     timeout: int = 120) -> Optional[Dict]:
        """
        Wait for pod to be ready and return timing metrics.
        Returns None if pod doesn't become ready.
        """
        start_time = time.time()

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

                # Check if ready
                conditions = status.get("conditions", [])
                is_ready = any(
                    c.get("type") == "Ready" and c.get("status") == "True"
                    for c in conditions
                )

                if is_ready or phase in ["Succeeded", "Failed"]:
                    return self._extract_pod_metrics(pod)

            except json.JSONDecodeError:
                pass

            time.sleep(1)

        success, output = self.run_kubectl(f"get pod {name} -n {namespace} -o json")
        if success:
            try:
                return self._extract_pod_metrics(json.loads(output))
            except:
                pass

        return None

    def _extract_pod_metrics(self, pod: dict) -> Dict:
        """Extract timing metrics from pod JSON"""
        metadata = pod.get("metadata", {})
        status = pod.get("status", {})
        spec = pod.get("spec", {})

        # Parse timestamps
        created_at = self._parse_timestamp(metadata.get("creationTimestamp"))

        # Get container statuses
        container_statuses = status.get("containerStatuses", [])
        init_container_statuses = status.get("initContainerStatuses", [])

        # Find ready time from conditions
        ready_at = None
        for condition in status.get("conditions", []):
            if condition.get("type") == "Ready" and condition.get("status") == "True":
                ready_at = self._parse_timestamp(condition.get("lastTransitionTime"))
                break

        # Find container start time
        container_started_at = None
        for cs in container_statuses:
            state = cs.get("state", {})
            if "running" in state:
                container_started_at = self._parse_timestamp(state["running"].get("startedAt"))
                break

        # Calculate init container duration
        init_duration = 0.0
        for ics in init_container_statuses:
            state = ics.get("state", {})
            if "terminated" in state:
                started = self._parse_timestamp(state["terminated"].get("startedAt"))
                finished = self._parse_timestamp(state["terminated"].get("finishedAt"))
                if started and finished:
                    init_duration += (finished - started).total_seconds()

        # Calculate total cold start
        total_cold_start = 0.0
        if created_at and ready_at:
            total_cold_start = (ready_at - created_at).total_seconds()

        # Calculate container create duration
        container_create_duration = 0.0
        if created_at and container_started_at:
            container_create_duration = (container_started_at - created_at).total_seconds()
            
            container_create_duration = max(0, container_create_duration - init_duration)

        return {
            "pod_name": metadata.get("name"),
            "created_at": metadata.get("creationTimestamp"),
            "ready_at": ready_at.isoformat() if ready_at else None,
            "container_started_at": container_started_at.isoformat() if container_started_at else None,
            "phase": status.get("phase"),
            "total_cold_start_seconds": total_cold_start,
            "container_create_duration_seconds": container_create_duration,
            "init_container_duration_seconds": init_duration,
            "init_container_count": len(spec.get("initContainers", [])),
        }

    def _parse_timestamp(self, ts: Optional[str]) -> Optional[datetime]:
        """Parse Kubernetes timestamp"""
        if not ts:
            return None
        try:
            
            if ts.endswith("Z"):
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return datetime.fromisoformat(ts)
        except:
            return None

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
                    "first_timestamp": item.get("firstTimestamp"),
                    "last_timestamp": item.get("lastTimestamp"),
                })
            return events
        except json.JSONDecodeError:
            return []

    def clear_image_cache(self, image: str) -> bool:
        """
        Clear image from node cache (Minikube specific).
        This forces a fresh pull next time.
        """
        logger.info(f"Clearing image cache for: {image}")
        success, output = self.run_kubectl(
            f"exec -it $(kubectl get nodes -o jsonpath='{{.items[0].metadata.name}}') -- "
            f"crictl rmi {image} 2>/dev/null || true",
            timeout=30
        )

        subprocess.run(
            f"minikube ssh 'docker rmi {image} 2>/dev/null || crictl rmi {image} 2>/dev/null' || true",
            shell=True,
            capture_output=True
        )
        return True


class ColdStartSubcauseExperiments:
    """Run experiments for each cold start sub-cause"""

    def __init__(self):
        self.k8s = KubernetesClient()
        self.samples = []

    def cleanup(self):
        """Clean up any existing test pods"""
        logger.info("Cleaning up existing test pods...")
        self.k8s.run_kubectl(
            f"delete pods -n {NAMESPACE} -l app=cold-start-experiment --ignore-not-found"
        )
        time.sleep(5)

    def run_single_experiment(self, pod_manifest: dict, sub_cause: str,
                               description: str, extra_metrics: dict = None) -> Optional[Dict]:
        """
        Run a single experiment: deploy pod, collect metrics, cleanup.

        Args:
            pod_manifest: Pod YAML manifest
            sub_cause: The sub-cause label for this experiment
            description: Human-readable description
            extra_metrics: Additional metrics to include

        Returns:
            Sample dict with all metrics, or None if failed
        """
        pod_name = pod_manifest["metadata"]["name"]

        logger.info(f"  Deploying pod: {pod_name}")

       
        self.k8s.delete_pod(pod_name)
        time.sleep(2)

        # Deploy the pod
        deploy_start = time.time()
        if not self.k8s.apply_yaml(pod_manifest):
            logger.error(f"  Failed to deploy pod")
            return None

        # Wait for pod to be ready 
        logger.info(f"  Waiting for pod to be ready...")
        pod_metrics = self.k8s.wait_for_pod(pod_name, timeout=180)

        if not pod_metrics:
            logger.warning(f"  Pod did not become ready, collecting partial metrics")
            pod_metrics = {}

        # Get pod events
        events = self.k8s.get_pod_events(pod_name)

        # Extract event-based metrics
        event_metrics = self._extract_event_metrics(events)

        # Build sample
        sample = {
            "timestamp": datetime.now().isoformat(),
            "sub_cause": sub_cause,
            "description": description,
            **pod_metrics,
            **event_metrics,
            "events": events,
        }

        # Add extra metrics if provided
        if extra_metrics:
            sample.update(extra_metrics)

        # Cleanup
        self.k8s.delete_pod(pod_name)

        logger.info(f"   Collected sample: total_cold_start={sample.get('total_cold_start_seconds', 0):.2f}s")

        return sample

    def _extract_event_metrics(self, events: List[Dict]) -> Dict:
        """Extract metrics from pod events"""
        metrics = {
            "image_pull_errors": 0,
            "image_pull_backoff": False,
            "image_not_found": False,
            "readiness_probe_failures": 0,
            "scheduling_failed": False,
        }

        for event in events:
            reason = event.get("reason", "")
            message = event.get("message", "").lower()
            count = event.get("count", 1)

            # Image pull issues
            if reason in ["Failed", "ErrImagePull", "ImagePullBackOff"]:
                metrics["image_pull_errors"] += count
            if reason == "ImagePullBackOff":
                metrics["image_pull_backoff"] = True
            if "not found" in message or "manifest unknown" in message:
                metrics["image_not_found"] = True

            # Probe failures
            if reason == "Unhealthy" and "readiness" in message.lower():
                metrics["readiness_probe_failures"] += count

            # Scheduling issues
            if reason in ["FailedScheduling", "Unschedulable"]:
                metrics["scheduling_failed"] = True

        return metrics

    
    # SUB-CAUSE 1: IMAGE PULL LATENCY
    

    def run_image_pull_latency_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Trigger image pull latency by using large images or clearing cache.

        Scenarios:
        - Use larger images (nginx, python, node)
        - Clear image cache before pull
        - First pull on node
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: image_pull_latency")
        logger.info("=" * 80)

        samples = []

        # Large images to test (ordered by size)
        test_images = [
            ("python:3.11-slim", 150),      # ~150MB
            ("node:18-slim", 200),          # ~200MB
            ("nginx:latest", 140),          # ~140MB
            ("python:3.11", 900),           # ~900MB (full image)
            ("node:18", 1000),              # ~1GB (full image)
        ]

        for i in range(num_samples):
            # Pick an image
            image, size_mb = test_images[i % len(test_images)]

            logger.info(f"\nSample {i+1}/{num_samples}: image_pull_latency with {image}")

            # Clear cache to force fresh pull (50% of the time)
            is_first_pull = random.random() < 0.5
            if is_first_pull:
                self.k8s.clear_image_cache(image)
                time.sleep(2)

            # Create pod manifest
            pod_manifest = self._create_pod_manifest(
                name=f"image-pull-test-{i}",
                image=image,
                command=["sh", "-c", "echo ready && sleep 60"]
            )

            # Run experiment
            sample = self.run_single_experiment(
                pod_manifest=pod_manifest,
                sub_cause="image_pull_latency",
                description=f"Large image pull: {image}",
                extra_metrics={
                    "image_size_estimate_mb": size_mb,
                    "is_first_pull_on_node": 1.0 if is_first_pull else 0.0,
                    "test_image": image,
                }
            )

            if sample:
                # Estimate image pull duration from total cold start
                # (subtract container create time and init time)
                total = sample.get("total_cold_start_seconds", 0)
                container_create = sample.get("container_create_duration_seconds", 0)
                init = sample.get("init_container_duration_seconds", 0)
                sample["image_pull_duration_seconds"] = max(0, total - container_create - init - 1)

                samples.append(sample)

            time.sleep(5)  # Cooldown between samples

        logger.info(f"\n Collected {len(samples)} image_pull_latency samples")
        return samples

    
    # SUB-CAUSE 2: INIT CONTAINER DELAY
    

    def run_init_container_delay_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Trigger init container delays by adding slow init containers.

        Scenarios:
        - Single init container with sleep
        - Multiple init containers
        - Init container with network wait
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: init_container_delay")
        logger.info("=" * 80)

        samples = []

        # Different init container configurations
        init_configs = [
            {"count": 1, "sleep": 10},
            {"count": 1, "sleep": 15},
            {"count": 2, "sleep": 8},
            {"count": 2, "sleep": 12},
            {"count": 3, "sleep": 5},
        ]

        for i in range(num_samples):
            config = init_configs[i % len(init_configs)]

            logger.info(f"\nSample {i+1}/{num_samples}: init_container_delay "
                       f"(count={config['count']}, sleep={config['sleep']}s)")

            # Create pod with init containers
            pod_manifest = self._create_pod_manifest(
                name=f"init-delay-test-{i}",
                image="busybox:latest",
                command=["sh", "-c", "echo ready && sleep 60"]
            )

            # Add init containers
            init_containers = []
            for j in range(config["count"]):
                init_containers.append({
                    "name": f"init-{j}",
                    "image": "busybox:latest",
                    "command": ["sh", "-c", f"echo 'Init container {j} sleeping...' && sleep {config['sleep']}"]
                })

            pod_manifest["spec"]["initContainers"] = init_containers

            # Run experiment
            sample = self.run_single_experiment(
                pod_manifest=pod_manifest,
                sub_cause="init_container_delay",
                description=f"Init containers: {config['count']} x {config['sleep']}s",
                extra_metrics={
                    "init_container_count": config["count"],
                    "expected_init_duration": config["count"] * config["sleep"],
                    "image_pull_duration_seconds": 0,  
                    "is_first_pull_on_node": 0,
                    "image_size_estimate_mb": 5,  
                }
            )

            if sample:
                samples.append(sample)

            time.sleep(5)

        logger.info(f"\n Collected {len(samples)} init_container_delay samples")
        return samples

    
    # SUB-CAUSE 3: READINESS PROBE FAILURE
    

    def run_readiness_probe_failure_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Trigger readiness probe failures by configuring probes that fail initially.

        Scenarios:
        - App starts slowly, probe fails multiple times
        - Short probe timeout
        - Wrong probe endpoint initially
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: readiness_probe_failure")
        logger.info("=" * 80)

        samples = []

        # Different probe failure configurations
        probe_configs = [
            {"initial_delay": 1, "period": 2, "failures_before_ready": 5},
            {"initial_delay": 1, "period": 3, "failures_before_ready": 4},
            {"initial_delay": 2, "period": 2, "failures_before_ready": 6},
            {"initial_delay": 1, "period": 5, "failures_before_ready": 3},
            {"initial_delay": 0, "period": 2, "failures_before_ready": 8},
        ]

        for i in range(num_samples):
            config = probe_configs[i % len(probe_configs)]

            # Calculate how long the app should "fail" before becoming ready
            fail_duration = config["failures_before_ready"] * config["period"]

            logger.info(f"\nSample {i+1}/{num_samples}: readiness_probe_failure "
                       f"(period={config['period']}s, expected_failures={config['failures_before_ready']})")

            # Create pod with readiness probe
            # The app will fail probe for fail_duration seconds, then pass
            pod_manifest = self._create_pod_manifest(
                name=f"probe-fail-test-{i}",
                image="busybox:latest",
                command=[
                    "sh", "-c",
                    f"touch /tmp/starting && sleep {fail_duration} && touch /tmp/ready && sleep 300"
                ]
            )

            # Add readiness probe that checks for /tmp/ready file
            pod_manifest["spec"]["containers"][0]["readinessProbe"] = {
                "exec": {
                    "command": ["cat", "/tmp/ready"]
                },
                "initialDelaySeconds": config["initial_delay"],
                "periodSeconds": config["period"],
                "timeoutSeconds": 1,
                "failureThreshold": 20,  
            }

            # Run experiment
            sample = self.run_single_experiment(
                pod_manifest=pod_manifest,
                sub_cause="readiness_probe_failure",
                description=f"Probe fails for {fail_duration}s before ready",
                extra_metrics={
                    "readiness_probe_period_seconds": config["period"],
                    "readiness_probe_timeout_seconds": 1,
                    "expected_probe_failures": config["failures_before_ready"],
                    "image_pull_duration_seconds": 0,
                    "is_first_pull_on_node": 0,
                    "image_size_estimate_mb": 5,
                    "init_container_count": 0,
                    "init_container_duration_seconds": 0,
                }
            )

            if sample:
                samples.append(sample)

            time.sleep(5)

        logger.info(f"\n Collected {len(samples)} readiness_probe_failure samples")
        return samples

    
    # SUB-CAUSE 4: CONTAINER RUNTIME SLOW
    

    def run_container_runtime_slow_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Simulate container runtime slowness.

        Since we can't easily slow down the container runtime itself,
        we simulate this by:
        - Using resource-heavy startup commands
        - Creating containers with high resource limits (causes slower allocation)
        - Running multiple containers that compete for resources

        Note: This is harder to trigger reliably in Minikube.
        We'll use a combination of techniques.
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: container_runtime_slow")
        logger.info("=" * 80)

        samples = []

        # Different scenarios to slow container creation
        scenarios = [
            {"cpu_limit": "1000m", "memory_limit": "512Mi", "startup_work": "dd if=/dev/zero bs=1M count=50 of=/dev/null"},
            {"cpu_limit": "500m", "memory_limit": "256Mi", "startup_work": "for i in $(seq 1 1000); do echo $i > /dev/null; done"},
            {"cpu_limit": "2000m", "memory_limit": "1Gi", "startup_work": "seq 1 100000 | sort -R > /dev/null"},
            {"cpu_limit": "100m", "memory_limit": "64Mi", "startup_work": "sleep 0.1"},  
        ]

        for i in range(num_samples):
            scenario = scenarios[i % len(scenarios)]

            logger.info(f"\nSample {i+1}/{num_samples}: container_runtime_slow")

            # Create pod with resource configuration
            pod_manifest = self._create_pod_manifest(
                name=f"runtime-slow-test-{i}",
                image="busybox:latest",
                command=["sh", "-c", f"{scenario['startup_work']} && echo ready && sleep 60"]
            )

            # Set resource limits
            pod_manifest["spec"]["containers"][0]["resources"] = {
                "requests": {
                    "cpu": "50m",
                    "memory": "32Mi"
                },
                "limits": {
                    "cpu": scenario["cpu_limit"],
                    "memory": scenario["memory_limit"]
                }
            }

            # Run experiment
            sample = self.run_single_experiment(
                pod_manifest=pod_manifest,
                sub_cause="container_runtime_slow",
                description=f"Container runtime with limits: {scenario['cpu_limit']}/{scenario['memory_limit']}",
                extra_metrics={
                    "cpu_limit": scenario["cpu_limit"],
                    "memory_limit": scenario["memory_limit"],
                    "image_pull_duration_seconds": 0,
                    "is_first_pull_on_node": 0,
                    "image_size_estimate_mb": 5,
                    "init_container_count": 0,
                    "init_container_duration_seconds": 0,
                    "readiness_probe_failures": 0,
                }
            )

            if sample:
                samples.append(sample)

            time.sleep(5)

        logger.info(f"\n Collected {len(samples)} container_runtime_slow samples")
        return samples

    
    # SUB-CAUSE 5: REGISTRY TIMEOUT
    

    def run_registry_timeout_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Trigger registry timeout/errors.

        Scenarios:
        - Use non-existent image tag (will fail then succeed with correct tag)
        - Use private registry without credentials
        - Use very slow registry (simulated by retrying after initial failure)

        Note: We can't easily simulate a slow registry, so we'll use images
        that cause pull errors/retries.
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: registry_timeout")
        logger.info("=" * 80)

        samples = []

        # Images that might cause registry issues or delays
        # Using a mix of real images and scenarios
        test_cases = [

            {"image": "alpine:3.18", "description": "Small image with potential cache miss"},
            {"image": "busybox:1.36", "description": "Specific version pull"},
            {"image": "nginx:1.25-alpine", "description": "Alpine nginx variant"},
            {"image": "registry.k8s.io/pause:3.9", "description": "K8s registry image"},
            {"image": "gcr.io/google-containers/busybox:latest", "description": "GCR registry"},
        ]

        for i in range(num_samples):
            test_case = test_cases[i % len(test_cases)]

            logger.info(f"\nSample {i+1}/{num_samples}: registry_timeout - {test_case['description']}")

            # Clear cache to force registry interaction
            self.k8s.clear_image_cache(test_case["image"])
            time.sleep(2)

            # Create pod
            pod_manifest = self._create_pod_manifest(
                name=f"registry-test-{i}",
                image=test_case["image"],
                command=["sh", "-c", "echo ready && sleep 60"]
            )

            # Run experiment
            sample = self.run_single_experiment(
                pod_manifest=pod_manifest,
                sub_cause="registry_timeout",
                description=test_case["description"],
                extra_metrics={
                    "test_image": test_case["image"],
                    "is_first_pull_on_node": 1.0,  
                    "image_size_estimate_mb": 10, 
                    "init_container_count": 0,
                    "init_container_duration_seconds": 0,
                }
            )

            if sample:
                # For registry timeout, image pull duration is the main factor
                total = sample.get("total_cold_start_seconds", 0)
                container_create = sample.get("container_create_duration_seconds", 0)
                sample["image_pull_duration_seconds"] = max(0, total - container_create - 1)

                samples.append(sample)

            time.sleep(5)

        logger.info(f"\n Collected {len(samples)} registry_timeout samples")
        return samples

    
    # HELPER METHODS
    

    def _create_pod_manifest(self, name: str, image: str, command: List[str]) -> Dict:
        """Create a pod manifest from template"""
        manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": name,
                "namespace": NAMESPACE,
                "labels": {
                    "app": "cold-start-experiment",
                    "experiment": "subcause"
                }
            },
            "spec": {
                "restartPolicy": "Never",
                "containers": [{
                    "name": "main",
                    "image": image,
                    "command": command,
                    "resources": {
                        "requests": {"cpu": "50m", "memory": "64Mi"},
                        "limits": {"cpu": "200m", "memory": "256Mi"}
                    }
                }]
            }
        }
        return manifest

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
        """Run all cold start sub-cause experiments"""
        logger.info("\n" + "=" * 80)
        logger.info("COLD START SUB-CAUSE DATA COLLECTION")
        logger.info("=" * 80 + "\n")

        self.cleanup()

        all_samples = {}

        # 1. Image Pull Latency
        samples = self.run_image_pull_latency_experiments(samples_per_subcause)
        all_samples["image_pull_latency"] = samples
        self.save_samples(samples, "image_pull_latency")
        time.sleep(10)

        # 2. Init Container Delay
        samples = self.run_init_container_delay_experiments(samples_per_subcause)
        all_samples["init_container_delay"] = samples
        self.save_samples(samples, "init_container_delay")
        time.sleep(10)

        # 3. Readiness Probe Failure
        samples = self.run_readiness_probe_failure_experiments(samples_per_subcause)
        all_samples["readiness_probe_failure"] = samples
        self.save_samples(samples, "readiness_probe_failure")
        time.sleep(10)

        # 4. Container Runtime Slow
        samples = self.run_container_runtime_slow_experiments(samples_per_subcause)
        all_samples["container_runtime_slow"] = samples
        self.save_samples(samples, "container_runtime_slow")
        time.sleep(10)

        # 5. Registry Timeout
        samples = self.run_registry_timeout_experiments(samples_per_subcause)
        all_samples["registry_timeout"] = samples
        self.save_samples(samples, "registry_timeout")

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

        # Final cleanup
        self.cleanup()

        return all_samples


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Collect cold start sub-cause data")
    parser.add_argument(
        "--samples", "-n",
        type=int,
        default=10,
        help="Number of samples per sub-cause (default: 10)"
    )
    parser.add_argument(
        "--subcause", "-s",
        choices=["image_pull_latency", "init_container_delay", "readiness_probe_failure",
                 "container_runtime_slow", "registry_timeout", "all"],
        default="all",
        help="Which sub-cause to collect data for (default: all)"
    )

    args = parser.parse_args()

    experiments = ColdStartSubcauseExperiments()

    if args.subcause == "all":
        experiments.run_all_experiments(args.samples)
    else:
        experiments.cleanup()

        if args.subcause == "image_pull_latency":
            samples = experiments.run_image_pull_latency_experiments(args.samples)
        elif args.subcause == "init_container_delay":
            samples = experiments.run_init_container_delay_experiments(args.samples)
        elif args.subcause == "readiness_probe_failure":
            samples = experiments.run_readiness_probe_failure_experiments(args.samples)
        elif args.subcause == "container_runtime_slow":
            samples = experiments.run_container_runtime_slow_experiments(args.samples)
        elif args.subcause == "registry_timeout":
            samples = experiments.run_registry_timeout_experiments(args.samples)

        experiments.save_samples(samples, args.subcause)
        experiments.cleanup()


if __name__ == "__main__":
    main()
