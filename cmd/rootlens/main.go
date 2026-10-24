package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/collector"
	"github.com/sandalichandrasekara/rootlens/pkg/config"
	"github.com/sandalichandrasekara/rootlens/pkg/rca"
	"github.com/sandalichandrasekara/rootlens/pkg/types"
	"github.com/sandalichandrasekara/rootlens/pkg/utils"
	"github.com/sandalichandrasekara/rootlens/pkg/workload"
)

func main() {
	logger := utils.NewLogger("RootLens")

	generateCmd := flag.NewFlagSet("generate", flag.ExitOnError)
	analyzeCmd := flag.NewFlagSet("analyze", flag.ExitOnError)
	monitorCmd := flag.NewFlagSet("monitor", flag.ExitOnError)
	purgeCmd := flag.NewFlagSet("purge", flag.ExitOnError)

	genMessageCount := generateCmd.Int("count", 1000, "Number of messages to generate")
	genMessageSize := generateCmd.Int("size", 1024, "Size of each message in bytes")
	genMode := generateCmd.String("mode", "spike", "Generation mode: spike or sustained")
	genRate := generateCmd.Int("rate", 100, "Messages per second (sustained mode only)")
	genDuration := generateCmd.Int("duration", 60, "Duration in seconds (sustained mode only)")

	analyzeNamespace := analyzeCmd.String("namespace", "default", "Kubernetes namespace")
	analyzeLabelSelector := analyzeCmd.String("selector", "app=consumer", "Pod label selector")

	monitorInterval := monitorCmd.Int("interval", 5, "Monitoring interval in seconds")
	monitorDuration := monitorCmd.Int("duration", 60, "Monitoring duration in seconds")
	monitorNamespace := monitorCmd.String("namespace", "default", "Kubernetes namespace")
	monitorSelector := monitorCmd.String("selector", "app=consumer", "Pod label selector")

	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	switch os.Args[1] {
	case "generate":
		generateCmd.Parse(os.Args[2:])
		handleGenerate(*genMessageCount, *genMessageSize, *genMode, *genRate, *genDuration, logger)

	case "analyze":
		analyzeCmd.Parse(os.Args[2:])
		handleAnalyze(*analyzeNamespace, *analyzeLabelSelector, logger)

	case "monitor":
		monitorCmd.Parse(os.Args[2:])
		handleMonitor(*monitorInterval, *monitorDuration, *monitorNamespace, *monitorSelector, logger)

	case "purge":
		purgeCmd.Parse(os.Args[2:])
		handlePurge(logger)

	default:
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println("RootLens - Automated Root Cause Diagnosis for KEDA Scaling Delays")
	fmt.Println("\nUsage:")
	fmt.Println("  rootlens <command> [flags]")
	fmt.Println("\nCommands:")
	fmt.Println("  generate   Generate workload spike in RabbitMQ")
	fmt.Println("  analyze    Perform one-time RCA analysis")
	fmt.Println("  monitor    Continuous monitoring and analysis")
	fmt.Println("  purge      Purge RabbitMQ queue")
	fmt.Println("\nExamples:")
	fmt.Println("  rootlens generate -count 5000 -size 1024")
	fmt.Println("  rootlens analyze -namespace default -selector app=consumer")
	fmt.Println("  rootlens monitor -interval 5 -duration 300")
	fmt.Println("  rootlens purge")
}

func handleGenerate(count, size int, mode string, rate, duration int, logger *utils.Logger) {
	config := getConfig()

	generator, err := workload.NewGenerator(
		config.RabbitMQ.Host,
		config.RabbitMQ.Port,
		config.RabbitMQ.Username,
		config.RabbitMQ.Password,
		config.RabbitMQ.QueueName,
		config.RabbitMQ.VHost,
		config.RabbitMQ.TLS,
	)
	if err != nil {
		logger.Error("Failed to create workload generator: %v", err)
		os.Exit(1)
	}
	defer generator.Close()

	if mode == "spike" {
		logger.Info("Generating spike: %d messages, %d bytes each", count, size)
		err = generator.GenerateSpike(count, size)
	} else if mode == "sustained" {
		logger.Info("Generating sustained load: %d msg/s for %d seconds", rate, duration)
		err = generator.GenerateSustained(rate, duration, size)
	} else {
		logger.Error("Invalid mode: %s (use 'spike' or 'sustained')", mode)
		os.Exit(1)
	}

	if err != nil {
		logger.Error("Failed to generate workload: %v", err)
		os.Exit(1)
	}

	depth, err := generator.GetQueueDepth()
	if err != nil {
		logger.Error("Failed to get queue depth: %v", err)
	} else {
		logger.Info("Current queue depth: %d messages", depth)
	}
}

func handleAnalyze(namespace, labelSelector string, logger *utils.Logger) {
	config := getConfig()

	logger.Info("Starting RCA analysis...")

	mgmtPort := managementPort(config.RabbitMQ.TLS)
	rabbitMQCollector := collector.NewRabbitMQCollector(
		config.RabbitMQ.Host,
		mgmtPort,
		config.RabbitMQ.Username,
		config.RabbitMQ.Password,
		config.RabbitMQ.QueueName,
		config.RabbitMQ.VHost,
		config.RabbitMQ.TLS,
	)

	homeDir, _ := os.UserHomeDir()
	kubeconfigPath := filepath.Join(homeDir, ".kube", "config")
	k8sCollector, err := collector.NewK8sCollector(kubeconfigPath, namespace)
	if err != nil {
		logger.Error("Failed to create K8s collector: %v", err)
		os.Exit(1)
	}

	rabbitMetrics, err := rabbitMQCollector.Collect()
	if err != nil {
		logger.Error("Failed to collect RabbitMQ metrics: %v", err)
		os.Exit(1)
	}

	podMetrics, err := k8sCollector.CollectPodMetrics(labelSelector)
	if err != nil {
		logger.Error("Failed to collect K8s metrics: %v", err)
		os.Exit(1)
	}

	telemetry := &types.TelemetryData{
		Timestamp:       time.Now(),
		RabbitMQMetrics: *rabbitMetrics,
		KEDAMetrics: types.KEDAMetrics{
			CurrentReplicas: len(podMetrics),
			DesiredReplicas: calculateDesiredReplicas(rabbitMetrics.MessageCount),
		},
	}

	rcaEngine := rca.NewEngine(config.RCA)
	result, err := rcaEngine.Analyze(telemetry, podMetrics)
	if err != nil {
		logger.Error("RCA analysis failed: %v", err)
		os.Exit(1)
	}

	printDiagnosticResult(result, logger)
}

func handleMonitor(interval, duration int, namespace, labelSelector string, logger *utils.Logger) {
	config := getConfig()

	logger.Info("Starting continuous monitoring (interval: %ds, duration: %ds)", interval, duration)

	timeout := time.After(time.Duration(duration) * time.Second)
	ticker := time.NewTicker(time.Duration(interval) * time.Second)
	defer ticker.Stop()

	mgmtPort := managementPort(config.RabbitMQ.TLS)
	rabbitMQCollector := collector.NewRabbitMQCollector(
		config.RabbitMQ.Host,
		mgmtPort,
		config.RabbitMQ.Username,
		config.RabbitMQ.Password,
		config.RabbitMQ.QueueName,
		config.RabbitMQ.VHost,
		config.RabbitMQ.TLS,
	)

	homeDir, _ := os.UserHomeDir()
	kubeconfigPath := filepath.Join(homeDir, ".kube", "config")
	k8sCollector, err := collector.NewK8sCollector(kubeconfigPath, namespace)
	if err != nil {
		logger.Error("Failed to create K8s collector: %v", err)
		os.Exit(1)
	}

	rcaEngine := rca.NewEngine(config.RCA)

	for {
		select {
		case <-timeout:
			logger.Info("Monitoring completed")
			return

		case <-ticker.C:
			rabbitMetrics, err := rabbitMQCollector.Collect()
			if err != nil {
				logger.Error("Failed to collect RabbitMQ metrics: %v", err)
				continue
			}

			podMetrics, err := k8sCollector.CollectPodMetrics(labelSelector)
			if err != nil {
				logger.Error("Failed to collect K8s metrics: %v", err)
				continue
			}

			telemetry := &types.TelemetryData{
				Timestamp:       time.Now(),
				RabbitMQMetrics: *rabbitMetrics,
				KEDAMetrics: types.KEDAMetrics{
					CurrentReplicas: len(podMetrics),
					DesiredReplicas: calculateDesiredReplicas(rabbitMetrics.MessageCount),
				},
			}

			result, err := rcaEngine.Analyze(telemetry, podMetrics)
			if err != nil {
				logger.Error("RCA analysis failed: %v", err)
				continue
			}

			if result.RootCause != types.Unknown {
				logger.Info("=== ISSUE DETECTED ===")
				printDiagnosticResult(result, logger)
			} else {
				logger.Info("Queue: %d messages, Pods: %d, Status: Normal",
					rabbitMetrics.MessageCount, len(podMetrics))
			}
		}
	}
}

func handlePurge(logger *utils.Logger) {
	config := getConfig()

	generator, err := workload.NewGenerator(
		config.RabbitMQ.Host,
		config.RabbitMQ.Port,
		config.RabbitMQ.Username,
		config.RabbitMQ.Password,
		config.RabbitMQ.QueueName,
		config.RabbitMQ.VHost,
		config.RabbitMQ.TLS,
	)
	if err != nil {
		logger.Error("Failed to connect to RabbitMQ: %v", err)
		os.Exit(1)
	}
	defer generator.Close()

	err = generator.PurgeQueue()
	if err != nil {
		logger.Error("Failed to purge queue: %v", err)
		os.Exit(1)
	}

	logger.Info("Queue purged successfully")
}

func getConfig() types.Config {
	return types.Config{
		RabbitMQ: config.LoadRabbitMQConfig(),
		RCA:      config.DefaultRCAConfig(),
	}
}

func managementPort(tls bool) int {
	if tls {
		return 443
	}
	return 15672
}

func calculateDesiredReplicas(queueDepth int) int {
	replicas := queueDepth / config.MessagesPerPod
	if replicas < 1 {
		replicas = 1
	}
	if replicas > 10 {
		replicas = 10
	}
	return replicas
}

func printDiagnosticResult(result *types.DiagnosticResult, logger *utils.Logger) {
	fmt.Println("    RootLens Diagnostic Result")
	fmt.Printf("Root Cause: %s\n", result.RootCause)
	fmt.Printf("Confidence: %.2f%%\n", result.Confidence*100)
	fmt.Printf("Detected At: %s\n\n", result.DetectedAt.Format("2006-01-02 15:04:05"))

	fmt.Println("Evidence:")
	for i, evidence := range result.Evidence {
		fmt.Printf("  %d. %s\n", i+1, evidence)
	}

	fmt.Println("\nRecommendations:")
	for i, rec := range result.Recommendations {
		fmt.Printf("  %d. %s\n", i+1, rec)
	}

	fmt.Println("\nMetrics:")
	for key, value := range result.Metrics {
		fmt.Printf("  %s: %v\n", key, value)
	}
}
