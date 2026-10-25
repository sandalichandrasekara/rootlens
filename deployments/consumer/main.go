package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/streadway/amqp"
)

func main() {
	rabbitHost := getEnv("RABBITMQ_HOST", "rabbitmq.rabbitmq.svc.cluster.local")
	rabbitUser := getEnv("RABBITMQ_USER", "admin")
	rabbitPass := getEnv("RABBITMQ_PASS", "")
	queueName := getEnv("QUEUE_NAME", "rootlens-tasks")

	if rabbitPass == "" {
		log.Fatal("RABBITMQ_PASS environment variable is required")
	}
	processingTime := getEnv("PROCESSING_TIME_MS", "100")

	connString := fmt.Sprintf("amqp://%s:%s@%s:5672/", rabbitUser, rabbitPass, rabbitHost)

	log.Printf("Connecting to RabbitMQ: %s", rabbitHost)

	conn, err := amqp.Dial(connString)
	if err != nil {
		log.Fatalf("Failed to connect to RabbitMQ: %v", err)
	}
	defer conn.Close()

	channel, err := conn.Channel()
	if err != nil {
		log.Fatalf("Failed to open channel: %v", err)
	}
	defer channel.Close()

	_, err = channel.QueueDeclare(queueName, true, false, false, false, nil)
	if err != nil {
		log.Fatalf("Failed to declare queue: %v", err)
	}

	err = channel.Qos(1, 0, false)
	if err != nil {
		log.Fatalf("Failed to set QoS: %v", err)
	}

	msgs, err := channel.Consume(queueName, "", false, false, false, false, nil)
	if err != nil {
		log.Fatalf("Failed to register consumer: %v", err)
	}

	log.Printf("Consumer started. Processing time: %sms per message", processingTime)

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	messageCount := 0

	go func() {
		for msg := range msgs {
			time.Sleep(time.Duration(mustAtoi(processingTime)) * time.Millisecond)

			msg.Ack(false)
			messageCount++

			if messageCount%10 == 0 {
				log.Printf("Processed %d messages", messageCount)
			}
		}
	}()

	<-sigChan
	log.Printf("Shutting down. Total messages processed: %d", messageCount)
}

func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

func mustAtoi(s string) int {
	var i int
	fmt.Sscanf(s, "%d", &i)
	if i == 0 {
		return 100
	}
	return i
}
