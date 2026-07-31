package workload

import (
	"fmt"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/utils"
	"github.com/streadway/amqp"
)

type Generator struct {
	conn       *amqp.Connection
	channel    *amqp.Channel
	queueName  string
	connString string
	logger     *utils.Logger
}

func NewGenerator(host string, port int, username, password, queueName, vhost string, useTLS bool) (*Generator, error) {
	logger := utils.NewLogger("WorkloadGenerator")

	protocol := "amqp"
	if useTLS {
		protocol = "amqps"
	}

	if vhost == "" || vhost == "/" {
		vhost = ""
	}
	connString := fmt.Sprintf("%s://%s:%s@%s:%d/%s", protocol, username, password, host, port, vhost)

	logger.Info("Connecting to RabbitMQ at %s:%d (TLS: %v, vhost: %s)", host, port, useTLS, vhost)

	conn, err := amqp.Dial(connString)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to RabbitMQ: %w", err)
	}

	channel, err := conn.Channel()
	if err != nil {
		conn.Close()
		return nil, fmt.Errorf("failed to open channel: %w", err)
	}

	_, err = channel.QueueDeclare(queueName, true, false, false, false, nil)
	if err != nil {
		channel.Close()
		conn.Close()
		return nil, fmt.Errorf("failed to declare queue: %w", err)
	}

	logger.Info("Connected to RabbitMQ, queue: %s", queueName)

	return &Generator{
		conn:       conn,
		channel:    channel,
		queueName:  queueName,
		connString: connString,
		logger:     logger,
	}, nil
}

// reconnect re-establishes the AMQP connection and channel if they have been closed.
func (g *Generator) reconnect() error {
	if g.conn != nil && !g.conn.IsClosed() {
		// Connection is fine; try to reopen just the channel.
		ch, err := g.conn.Channel()
		if err == nil {
			g.channel = ch
			_, err = g.channel.QueueDeclare(g.queueName, true, false, false, false, nil)
			if err == nil {
				return nil
			}
		}
		// Channel re-open failed - fall through and reconnect fully.
	}

	g.logger.Info("Reconnecting to RabbitMQ...")
	conn, err := amqp.Dial(g.connString)
	if err != nil {
		return fmt.Errorf("reconnect failed: %w", err)
	}

	ch, err := conn.Channel()
	if err != nil {
		conn.Close()
		return fmt.Errorf("failed to open channel after reconnect: %w", err)
	}

	_, err = ch.QueueDeclare(g.queueName, true, false, false, false, nil)
	if err != nil {
		ch.Close()
		conn.Close()
		return fmt.Errorf("failed to declare queue after reconnect: %w", err)
	}

	g.conn = conn
	g.channel = ch
	g.logger.Info("Reconnected to RabbitMQ successfully")
	return nil
}

func (g *Generator) Close() error {
	if g.channel != nil {
		g.channel.Close()
	}
	if g.conn != nil {
		return g.conn.Close()
	}
	return nil
}

// GenerateSpike sends a burst of messages to simulate load spike
func (g *Generator) GenerateSpike(messageCount int, messageSize int) error {
	if err := g.reconnect(); err != nil {
		return err
	}
	g.logger.Info("Starting message spike: %d messages", messageCount)

	startTime := time.Now()

	payload := make([]byte, messageSize)
	for i := range payload {
		payload[i] = byte(i % 256)
	}

	for i := 0; i < messageCount; i++ {
		msg := amqp.Publishing{
			DeliveryMode: amqp.Persistent,
			ContentType:  "application/octet-stream",
			Body:         payload,
			Timestamp:    time.Now(),
		}

		err := g.channel.Publish(
			"",          // exchange
			g.queueName, // routing key
			false,       // mandatory
			false,       // immediate
			msg,
		)

		if err != nil {
			return fmt.Errorf("failed to publish message %d: %w", i, err)
		}

		if (i+1)%100 == 0 {
			g.logger.Info("Published %d/%d messages", i+1, messageCount)
		}
	}

	duration := time.Since(startTime)
	g.logger.Info("Spike complete: %d messages in %.2f seconds (%.2f msg/s)",
		messageCount, duration.Seconds(), float64(messageCount)/duration.Seconds())

	return nil
}

// GenerateSustained sends messages at a constant rate
func (g *Generator) GenerateSustained(messagesPerSecond int, durationSeconds int, messageSize int) error {
	if err := g.reconnect(); err != nil {
		return err
	}
	g.logger.Info("Starting sustained load: %d msg/s for %d seconds", messagesPerSecond, durationSeconds)

	interval := time.Second / time.Duration(messagesPerSecond)
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	timeout := time.After(time.Duration(durationSeconds) * time.Second)

	payload := make([]byte, messageSize)
	for i := range payload {
		payload[i] = byte(i % 256)
	}

	messageCount := 0

	for {
		select {
		case <-timeout:
			g.logger.Info("Sustained load complete: %d messages sent", messageCount)
			return nil

		case <-ticker.C:
			msg := amqp.Publishing{
				DeliveryMode: amqp.Persistent,
				ContentType:  "application/octet-stream",
				Body:         payload,
				Timestamp:    time.Now(),
			}

			err := g.channel.Publish("", g.queueName, false, false, msg)
			if err != nil {
				return fmt.Errorf("failed to publish message: %w", err)
			}

			messageCount++

			if messageCount%100 == 0 {
				g.logger.Info("Published %d messages", messageCount)
			}
		}
	}
}

// PurgeQueue removes all messages from the queue
func (g *Generator) PurgeQueue() error {
	if err := g.reconnect(); err != nil {
		return err
	}
	g.logger.Info("Purging queue: %s", g.queueName)

	_, err := g.channel.QueuePurge(g.queueName, false)
	if err != nil {
		return fmt.Errorf("failed to purge queue: %w", err)
	}

	g.logger.Info("Queue purged successfully")
	return nil
}

// GetQueueDepth returns the current number of messages in the queue
func (g *Generator) GetQueueDepth() (int, error) {
	queue, err := g.channel.QueueInspect(g.queueName)
	if err != nil {
		return 0, fmt.Errorf("failed to inspect queue: %w", err)
	}

	return queue.Messages, nil
}
