package main

import (
	"fmt"
	"log"
	"net/http"

	"github.com/joho/godotenv"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/sandalichandrasekara/rootlens/pkg/api"
	"github.com/sandalichandrasekara/rootlens/pkg/config"
	"github.com/sandalichandrasekara/rootlens/pkg/metrics"
	"github.com/sandalichandrasekara/rootlens/pkg/storage"
	"github.com/sandalichandrasekara/rootlens/pkg/types"
)

func main() {
	godotenv.Load()

	fmt.Println("  RootLens Dashboard Server")

	store := storage.NewStore()
	cfg := types.Config{
		RabbitMQ: config.LoadRabbitMQConfig(),
		RCA:      config.DefaultRCAConfig(),
		ML:       config.LoadMLConfig(),
	}

	metrics.MLServiceAvailable.Set(0)
	metrics.QueueDepth.Set(0)
	metrics.QueueConsumers.Set(0)
	metrics.KEDACurrentReplicas.Set(0)
	metrics.KEDADesiredReplicas.Set(0)

	server, err := api.NewServer(store, cfg)
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.HandleFunc("/api/health", api.JSONContentType(server.HandleHealthCheck))
	mux.HandleFunc("/api/metrics", api.JSONContentType(server.HandleGetMetrics))
	mux.HandleFunc("/api/rca/run", api.JSONContentType(api.EnforceJSONContentType(server.HandleRunRCA)))
	mux.HandleFunc("/api/rca/latest", api.JSONContentType(server.HandleGetLatestRCA))
	mux.HandleFunc("/api/rca/history", api.JSONContentType(server.HandleGetRCAHistory))
	mux.HandleFunc("/api/rca/stats", api.JSONContentType(server.HandleGetRCAStats))
	mux.HandleFunc("/api/rca/clear", api.JSONContentType(server.HandleClearRCAHistory))
	mux.HandleFunc("/api/rca/test", api.JSONContentType(api.EnforceJSONContentType(server.HandleTestRCA)))
	mux.HandleFunc("/api/workload/generate", api.JSONContentType(api.EnforceJSONContentType(server.HandleGenerateWorkload)))
	mux.HandleFunc("/api/workload/purge", api.JSONContentType(api.EnforceJSONContentType(server.HandlePurgeQueue)))

	handler := api.SecurityHeaders(api.CORSMiddleware(api.InstrumentRequests(mux)))

	port := ":8080"
	fmt.Printf("\n Server starting on http://localhost%s\n", port)
	fmt.Println("\nAPI Endpoints:")
	fmt.Println("  GET  /metrics          (Prometheus format)")
	fmt.Println("  GET  /api/health")
	fmt.Println("  GET  /api/metrics      (JSON format)")
	fmt.Println("  POST /api/rca/run")
	fmt.Println("  GET  /api/rca/latest")
	fmt.Println("  POST /api/rca/test")
	fmt.Println("  GET  /api/rca/history")
	fmt.Println("  GET  /api/rca/stats")
	fmt.Println("  DEL  /api/rca/clear")
	fmt.Println("  POST /api/workload/generate")
	fmt.Println("  POST /api/workload/purge")

	if err := http.ListenAndServe(port, handler); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
