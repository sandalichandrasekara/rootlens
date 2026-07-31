.PHONY: build test run clean deps setup-cluster fmt lint

build:
	@echo "Building RootLens..."
	@mkdir -p bin
	@go build -o bin/rootlens cmd/rootlens/main.go
	@echo "✓ Build complete: bin/rootlens"

test:
	@echo "Running tests..."
	@go test ./... -v

run:
	@echo "Running RootLens..."
	@go run cmd/rootlens/main.go

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf bin/
	@echo "✓ Clean complete"

deps:
	@echo "Installing dependencies..."
	@go mod download
	@go mod tidy
	@echo "✓ Dependencies installed"

setup-cluster:
	@echo "Setting up Kubernetes cluster..."
	@bash scripts/setup-cluster.sh

fmt:
	@echo "Formatting code..."
	@go fmt ./...
	@echo "✓ Code formatted"

lint:
	@echo "Running linter..."
	@golangci-lint run || echo "Install golangci-lint for linting"

.DEFAULT_GOAL := build