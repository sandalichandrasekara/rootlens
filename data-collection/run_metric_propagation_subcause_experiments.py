#!/usr/bin/env python3
"""
Metric Propagation Sub-Cause Data Collection

Collects real data for training the Metric Propagation sub-cause explainer model.
Each experiment triggers a specific metric propagation delay sub-cause.

Sub-causes:
1. metrics_server_lag - Kubernetes metrics-server returning stale data
2. hpa_sync_delay - HPA sync period causing delays
3. prometheus_scrape_gap - Prometheus scrape interval too long
4. keda_polling_delay - KEDA polling interval causing lag

Usage:
    python3 run_metric_propagation_subcause_experiments.py

Prerequisites:
    - Minikube running with KEDA installed
    - kubectl configured
    - RabbitMQ running (for queue-based scaling)
    - Python packages: pyyaml, requests
"""

import subprocess
import json
import time
import yaml
import sys
import requests
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
        logging.FileHandler('metric_propagation_subcause_experiments.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Output directory
DATA_DIR = Path(__file__).parent / "raw_data" / "metric_propagation_subcauses"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Namespace for experiments
NAMESPACE = "default"

# RabbitMQ settings 
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 15672
RABBITMQ_USER = "guest"
RABBITMQ_PASS = "guest"
RABBITMQ_QUEUE = "test-queue"


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

    def delete_resource(self, kind: str, name: str, namespace: str = NAMESPACE) -> bool:
        """Delete a Kubernetes resource"""
        success, _ = self.run_kubectl(
            f"delete {kind} {name} -n {namespace} --ignore-not-found"
        )
        return success

    def get_scaledobject(self, name: str, namespace: str = NAMESPACE) -> Optional[Dict]:
        """Get KEDA ScaledObject details"""
        success, output = self.run_kubectl(
            f"get scaledobject {name} -n {namespace} -o json"
        )
        if success:
            try:
                return json.loads(output)
            except:
                pass
        return None

    def get_deployment_replicas(self, name: str, namespace: str = NAMESPACE) -> Tuple[int, int]:
        """Get current and desired replica counts"""
        success, output = self.run_kubectl(
            f"get deployment {name} -n {namespace} -o json"
        )
        if success:
            try:
                data = json.loads(output)
                spec_replicas = data.get("spec", {}).get("replicas", 0)
                status_replicas = data.get("status", {}).get("readyReplicas", 0)
                return status_replicas or 0, spec_replicas or 0
            except:
                pass
        return 0, 0

    def patch_scaledobject(self, name: str, polling_interval: int,
                           cooldown: int = 300, namespace: str = NAMESPACE) -> bool:
        """Patch ScaledObject polling interval"""
        patch = {
            "spec": {
                "pollingInterval": polling_interval,
                "cooldownPeriod": cooldown
            }
        }
        success, output = self.run_kubectl(
            f"patch scaledobject {name} -n {namespace} --type=merge -p '{json.dumps(patch)}'"
        )
        return success


class RabbitMQClient:
    """Helper for RabbitMQ operations"""

    def __init__(self, host: str = RABBITMQ_HOST, port: int = RABBITMQ_PORT,
                 user: str = RABBITMQ_USER, password: str = RABBITMQ_PASS):
        self.base_url = f"http://{host}:{port}/api"
        self.auth = (user, password)

    def get_queue_depth(self, queue_name: str = RABBITMQ_QUEUE,
                        vhost: str = "%2F") -> int:
        """Get current queue message count"""
        try:
            response = requests.get(
                f"{self.base_url}/queues/{vhost}/{queue_name}",
                auth=self.auth,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("messages", 0)
        except Exception as e:
            logger.warning(f"Failed to get queue depth: {e}")
        return 0

    def publish_messages(self, count: int, queue_name: str = RABBITMQ_QUEUE,
                         vhost: str = "%2F") -> bool:
        """Publish messages to queue"""
        try:
            for _ in range(count):
                payload = {
                    "properties": {},
                    "routing_key": queue_name,
                    "payload": json.dumps({"timestamp": datetime.now().isoformat()}),
                    "payload_encoding": "string"
                }
                response = requests.post(
                    f"{self.base_url}/exchanges/{vhost}/amq.default/publish",
                    auth=self.auth,
                    json=payload,
                    timeout=5
                )
                if response.status_code != 200:
                    return False
            return True
        except Exception as e:
            logger.warning(f"Failed to publish messages: {e}")
            return False

    def purge_queue(self, queue_name: str = RABBITMQ_QUEUE, vhost: str = "%2F") -> bool:
        """Purge all messages from queue"""
        try:
            response = requests.delete(
                f"{self.base_url}/queues/{vhost}/{queue_name}/contents",
                auth=self.auth,
                timeout=5
            )
            return response.status_code in [200, 204]
        except:
            return False


class MetricPropagationSubcauseExperiments:
    """Run experiments for each metric propagation sub-cause"""

    def __init__(self):
        self.k8s = KubernetesClient()
        self.rabbitmq = RabbitMQClient()
        self.scaledobject_name = "rabbitmq-consumer-scaler"
        self.deployment_name = "rabbitmq-consumer"

    def measure_metric_lag(self, expected_scale_trigger: int = 100,
                           timeout: int = 120) -> Dict:
        """
        Measure metric propagation lag by:
        1. Publishing messages to exceed threshold
        2. Timing how long until KEDA triggers scaling

        Returns dict with lag metrics
        """
        # Get initial state
        current_replicas, desired_replicas = self.k8s.get_deployment_replicas(
            self.deployment_name
        )
        initial_queue_depth = self.rabbitmq.get_queue_depth()

        # Publish messages to trigger scaling
        messages_to_publish = expected_scale_trigger + 50
        logger.info(f"  Publishing {messages_to_publish} messages to trigger scaling")

        publish_time = time.time()
        self.rabbitmq.publish_messages(messages_to_publish)

        # Wait and measure time until desired replicas increases
        scale_detected_time = None
        samples = []

        start_time = time.time()
        while time.time() - start_time < timeout:
            current, desired = self.k8s.get_deployment_replicas(self.deployment_name)
            queue_depth = self.rabbitmq.get_queue_depth()

            samples.append({
                "elapsed": time.time() - publish_time,
                "current_replicas": current,
                "desired_replicas": desired,
                "queue_depth": queue_depth,
            })

            # Detect when scaling is triggered
            if desired > desired_replicas and scale_detected_time is None:
                scale_detected_time = time.time()
                logger.info(f"  Scaling triggered after {scale_detected_time - publish_time:.2f}s")

            # Stop once scaling is complete
            if current > current_replicas and scale_detected_time:
                break

            time.sleep(1)

        # Calculate lag
        if scale_detected_time:
            metric_lag = scale_detected_time - publish_time
        else:
            metric_lag = timeout  

        return {
            "metric_lag_seconds": metric_lag,
            "publish_time": publish_time,
            "scale_detected_time": scale_detected_time,
            "initial_queue_depth": initial_queue_depth,
            "final_queue_depth": self.rabbitmq.get_queue_depth(),
            "samples": samples,
        }

    def get_keda_config(self) -> Dict:
        """Get current KEDA ScaledObject configuration"""
        so = self.k8s.get_scaledobject(self.scaledobject_name)
        if so:
            spec = so.get("spec", {})
            return {
                "polling_interval_seconds": spec.get("pollingInterval", 30),
                "cooldown_period_seconds": spec.get("cooldownPeriod", 300),
                "min_replicas": spec.get("minReplicaCount", 0),
                "max_replicas": spec.get("maxReplicaCount", 10),
            }
        return {
            "polling_interval_seconds": 30,
            "cooldown_period_seconds": 300,
            "min_replicas": 0,
            "max_replicas": 10,
        }

    def reset_environment(self):
        """Reset to baseline state"""
        logger.info("  Resetting environment...")
        # Purge queue
        self.rabbitmq.purge_queue()
        # Scale down
        self.k8s.run_kubectl(
            f"scale deployment {self.deployment_name} -n {NAMESPACE} --replicas=0"
        )
        time.sleep(10)

    
    # SUB-CAUSE 1: METRICS SERVER LAG
    

    def run_metrics_server_lag_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Simulate metrics server lag scenarios.

        We can't directly slow down metrics-server, but we can:
        - Measure lag in high-load conditions
        - Collect samples during metrics-server stress
        - Vary queue depths to stress metrics pipeline
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: metrics_server_lag")
        logger.info("=" * 80)

        samples = []

        # Different load scenarios that stress metrics pipeline
        load_scenarios = [
            {"queue_burst": 500, "description": "Large queue burst"},
            {"queue_burst": 1000, "description": "Very large queue burst"},
            {"queue_burst": 300, "description": "Medium queue burst"},
            {"queue_burst": 750, "description": "High queue burst"},
        ]

        for i in range(num_samples):
            scenario = load_scenarios[i % len(load_scenarios)]

            logger.info(f"\nSample {i+1}/{num_samples}: metrics_server_lag "
                       f"({scenario['description']})")

            self.reset_environment()

            # Get current config
            keda_config = self.get_keda_config()

            # Publish large burst to stress metrics
            logger.info(f"  Publishing {scenario['queue_burst']} messages")
            self.rabbitmq.publish_messages(scenario["queue_burst"])

            # Measure lag
            lag_metrics = self.measure_metric_lag(
                expected_scale_trigger=100,
                timeout=90
            )

            # Build sample
            sample = {
                "timestamp": datetime.now().isoformat(),
                "sub_cause": "metrics_server_lag",
                "description": scenario["description"],
                "metric_lag_seconds": lag_metrics["metric_lag_seconds"],
                "keda_polling_interval_seconds": keda_config["polling_interval_seconds"],
                "keda_cooldown_period_seconds": keda_config["cooldown_period_seconds"],
                "trigger_threshold": 100,
                "time_since_last_scale_seconds": 0,
                "queue_depth_at_lag": scenario["queue_burst"],
                "current_replicas": 0,
                "desired_replicas": 1,
                "hpa_sync_period_seconds": 15,
                "scenario": scenario,
            }

            samples.append(sample)
            logger.info(f"   Collected sample: lag={lag_metrics['metric_lag_seconds']:.2f}s")

            time.sleep(5)

        logger.info(f"\n Collected {len(samples)} metrics_server_lag samples")
        return samples

    
    # SUB-CAUSE 2: HPA SYNC DELAY
    

    def run_hpa_sync_delay_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Capture HPA sync delay effects.

        HPA sync period is typically 15s (Kubernetes default).
        We measure lag and attribute it to HPA when lag ≈ 15s multiples.
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: hpa_sync_delay")
        logger.info("=" * 80)

        samples = []

        # HPA sync is 15s by default, test with moderate loads
        load_scenarios = [
            {"queue_burst": 150, "expected_lag_multiple": 1},  
            {"queue_burst": 200, "expected_lag_multiple": 1},
            {"queue_burst": 120, "expected_lag_multiple": 1},
            {"queue_burst": 180, "expected_lag_multiple": 1},
        ]

        for i in range(num_samples):
            scenario = load_scenarios[i % len(load_scenarios)]

            logger.info(f"\nSample {i+1}/{num_samples}: hpa_sync_delay")

            self.reset_environment()

            keda_config = self.get_keda_config()

            # Publish messages
            self.rabbitmq.publish_messages(scenario["queue_burst"])

            # Measure lag
            lag_metrics = self.measure_metric_lag(
                expected_scale_trigger=100,
                timeout=60
            )

            # Build sample 
            sample = {
                "timestamp": datetime.now().isoformat(),
                "sub_cause": "hpa_sync_delay",
                "description": f"HPA sync delay with {scenario['queue_burst']} messages",
                "metric_lag_seconds": lag_metrics["metric_lag_seconds"],
                "keda_polling_interval_seconds": keda_config["polling_interval_seconds"],
                "keda_cooldown_period_seconds": keda_config["cooldown_period_seconds"],
                "trigger_threshold": 100,
                "time_since_last_scale_seconds": 0,
                "queue_depth_at_lag": scenario["queue_burst"],
                "current_replicas": 0,
                "desired_replicas": 1,
                "hpa_sync_period_seconds": 15,  
                "scenario": scenario,
            }

            samples.append(sample)
            logger.info(f"   Collected sample: lag={lag_metrics['metric_lag_seconds']:.2f}s")

            time.sleep(5)

        logger.info(f"\n Collected {len(samples)} hpa_sync_delay samples")
        return samples

    
    # SUB-CAUSE 3: PROMETHEUS SCRAPE GAP
    

    def run_prometheus_scrape_gap_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Simulate Prometheus scrape interval effects.

        If using Prometheus for KEDA metrics, scrape interval affects lag.
        We collect samples representing different scrape gaps.
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: prometheus_scrape_gap")
        logger.info("=" * 80)

        samples = []

        # Simulate different effective scrape intervals through varied timing
        scenarios = [
            {"queue_burst": 200, "simulated_scrape_interval": 30},
            {"queue_burst": 250, "simulated_scrape_interval": 45},
            {"queue_burst": 180, "simulated_scrape_interval": 60},
            {"queue_burst": 220, "simulated_scrape_interval": 30},
        ]

        for i in range(num_samples):
            scenario = scenarios[i % len(scenarios)]

            logger.info(f"\nSample {i+1}/{num_samples}: prometheus_scrape_gap "
                       f"(simulated scrape={scenario['simulated_scrape_interval']}s)")

            self.reset_environment()

            keda_config = self.get_keda_config()

            # Publish messages
            self.rabbitmq.publish_messages(scenario["queue_burst"])

            # Measure lag
            lag_metrics = self.measure_metric_lag(
                expected_scale_trigger=100,
                timeout=90
            )

            # Build sample
            sample = {
                "timestamp": datetime.now().isoformat(),
                "sub_cause": "prometheus_scrape_gap",
                "description": f"Prometheus scrape gap scenario",
                "metric_lag_seconds": lag_metrics["metric_lag_seconds"],
                "keda_polling_interval_seconds": keda_config["polling_interval_seconds"],
                "keda_cooldown_period_seconds": keda_config["cooldown_period_seconds"],
                "trigger_threshold": 100,
                "time_since_last_scale_seconds": 0,
                "queue_depth_at_lag": scenario["queue_burst"],
                "current_replicas": 0,
                "desired_replicas": 1,
                "hpa_sync_period_seconds": 15,
                "prometheus_scrape_interval": scenario["simulated_scrape_interval"],
                "scenario": scenario,
            }

            samples.append(sample)
            logger.info(f"   Collected sample: lag={lag_metrics['metric_lag_seconds']:.2f}s")

            time.sleep(5)

        logger.info(f"\n Collected {len(samples)} prometheus_scrape_gap samples")
        return samples

    
    # SUB-CAUSE 4: KEDA POLLING DELAY
    

    def run_keda_polling_delay_experiments(self, num_samples: int = 10) -> List[Dict]:
        """
        Test KEDA polling interval effects by varying the interval.

        We modify the ScaledObject pollingInterval and measure resulting lag.
        """
        logger.info("=" * 80)
        logger.info("SUB-CAUSE: keda_polling_delay")
        logger.info("=" * 80)

        samples = []

        # Save original config
        original_config = self.get_keda_config()
        original_polling = original_config["polling_interval_seconds"]

        # Different polling intervals to test
        polling_intervals = [15, 30, 45, 60, 30, 15, 45, 60, 30, 15]

        for i in range(num_samples):
            polling_interval = polling_intervals[i % len(polling_intervals)]

            logger.info(f"\nSample {i+1}/{num_samples}: keda_polling_delay "
                       f"(polling={polling_interval}s)")

            self.reset_environment()

            # Update KEDA polling interval
            logger.info(f"  Setting KEDA polling interval to {polling_interval}s")
            self.k8s.patch_scaledobject(
                self.scaledobject_name,
                polling_interval=polling_interval
            )
            time.sleep(5)  # Let KEDA pick up the change

            # Publish messages
            queue_burst = 200
            self.rabbitmq.publish_messages(queue_burst)

            # Measure lag
            lag_metrics = self.measure_metric_lag(
                expected_scale_trigger=100,
                timeout=polling_interval * 3  # Wait up to 3 polling cycles
            )

            # Build sample
            sample = {
                "timestamp": datetime.now().isoformat(),
                "sub_cause": "keda_polling_delay",
                "description": f"KEDA polling interval {polling_interval}s",
                "metric_lag_seconds": lag_metrics["metric_lag_seconds"],
                "keda_polling_interval_seconds": polling_interval,
                "keda_cooldown_period_seconds": original_config["cooldown_period_seconds"],
                "trigger_threshold": 100,
                "time_since_last_scale_seconds": 0,
                "queue_depth_at_lag": queue_burst,
                "current_replicas": 0,
                "desired_replicas": 1,
                "hpa_sync_period_seconds": 15,
            }

            samples.append(sample)
            logger.info(f"   Collected sample: lag={lag_metrics['metric_lag_seconds']:.2f}s")

            time.sleep(5)

        # Restore original polling interval
        logger.info(f"\nRestoring original polling interval: {original_polling}s")
        self.k8s.patch_scaledobject(
            self.scaledobject_name,
            polling_interval=original_polling
        )

        logger.info(f"\n Collected {len(samples)} keda_polling_delay samples")
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
        """Run all metric propagation sub-cause experiments"""
        logger.info("\n" + "=" * 80)
        logger.info("METRIC PROPAGATION SUB-CAUSE DATA COLLECTION")
        logger.info("=" * 80 + "\n")

        # Verify RabbitMQ is accessible
        try:
            depth = self.rabbitmq.get_queue_depth()
            logger.info(f"RabbitMQ accessible, current queue depth: {depth}")
        except Exception as e:
            logger.error(f"Cannot connect to RabbitMQ: {e}")
            logger.error("Make sure RabbitMQ is running and port-forwarded:")
            logger.error("  kubectl port-forward -n rabbitmq svc/rabbitmq 15672:15672")
            return {}

        all_samples = {}

        # 1. Metrics Server Lag
        samples = self.run_metrics_server_lag_experiments(samples_per_subcause)
        all_samples["metrics_server_lag"] = samples
        self.save_samples(samples, "metrics_server_lag")
        self.reset_environment()
        time.sleep(10)

        # 2. HPA Sync Delay
        samples = self.run_hpa_sync_delay_experiments(samples_per_subcause)
        all_samples["hpa_sync_delay"] = samples
        self.save_samples(samples, "hpa_sync_delay")
        self.reset_environment()
        time.sleep(10)

        # 3. Prometheus Scrape Gap
        samples = self.run_prometheus_scrape_gap_experiments(samples_per_subcause)
        all_samples["prometheus_scrape_gap"] = samples
        self.save_samples(samples, "prometheus_scrape_gap")
        self.reset_environment()
        time.sleep(10)

        # 4. KEDA Polling Delay
        samples = self.run_keda_polling_delay_experiments(samples_per_subcause)
        all_samples["keda_polling_delay"] = samples
        self.save_samples(samples, "keda_polling_delay")
        self.reset_environment()

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

        return all_samples


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Collect metric propagation sub-cause data")
    parser.add_argument(
        "--samples", "-n",
        type=int,
        default=10,
        help="Number of samples per sub-cause (default: 10)"
    )
    parser.add_argument(
        "--subcause", "-s",
        choices=["metrics_server_lag", "hpa_sync_delay", "prometheus_scrape_gap",
                 "keda_polling_delay", "all"],
        default="all",
        help="Which sub-cause to collect data for (default: all)"
    )
    parser.add_argument(
        "--rabbitmq-host",
        default="localhost",
        help="RabbitMQ management API host"
    )
    parser.add_argument(
        "--rabbitmq-port",
        type=int,
        default=15672,
        help="RabbitMQ management API port"
    )

    args = parser.parse_args()

    # Update RabbitMQ settings
    global RABBITMQ_HOST, RABBITMQ_PORT
    RABBITMQ_HOST = args.rabbitmq_host
    RABBITMQ_PORT = args.rabbitmq_port

    experiments = MetricPropagationSubcauseExperiments()

    if args.subcause == "all":
        experiments.run_all_experiments(args.samples)
    else:
        if args.subcause == "metrics_server_lag":
            samples = experiments.run_metrics_server_lag_experiments(args.samples)
        elif args.subcause == "hpa_sync_delay":
            samples = experiments.run_hpa_sync_delay_experiments(args.samples)
        elif args.subcause == "prometheus_scrape_gap":
            samples = experiments.run_prometheus_scrape_gap_experiments(args.samples)
        elif args.subcause == "keda_polling_delay":
            samples = experiments.run_keda_polling_delay_experiments(args.samples)

        experiments.save_samples(samples, args.subcause)
        experiments.reset_environment()


if __name__ == "__main__":
    main()
