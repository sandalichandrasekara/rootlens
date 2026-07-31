package collector

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/types"
)

type RabbitMQCollector struct {
	host      string
	port      int
	username  string
	password  string
	queueName string
	vhost     string
	useTLS    bool
	client    *http.Client
}

func NewRabbitMQCollector(host string, port int, username, password, queueName, vhost string, useTLS bool) *RabbitMQCollector {
	return &RabbitMQCollector{
		host:      host,
		port:      port,
		username:  username,
		password:  password,
		queueName: queueName,
		vhost:     vhost,
		useTLS:    useTLS,
		client:    &http.Client{Timeout: 10 * time.Second},
	}
}

func (r *RabbitMQCollector) Collect() (*types.RabbitMQMetrics, error) {
	protocol := "http"
	if r.useTLS {
		protocol = "https"
	}

	vhost := "%2F"
	if r.vhost != "" && r.vhost != "/" {
		vhost = r.vhost
	}

	var url string
	if r.useTLS {
		url = fmt.Sprintf("%s://%s/api/queues/%s/%s", protocol, r.host, vhost, r.queueName)
	} else {
		url = fmt.Sprintf("%s://%s:%d/api/queues/%s/%s", protocol, r.host, r.port, vhost, r.queueName)
	}

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.SetBasicAuth(r.username, r.password)

	resp, err := r.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to get queue stats: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var queueInfo struct {
		Messages        int `json:"messages"`
		Consumers       int `json:"consumers"`
		MessagesReady   int `json:"messages_ready"`
		MessagesDetails struct {
			Rate float64 `json:"rate"`
		} `json:"messages_details"`
	}

	if err := json.Unmarshal(body, &queueInfo); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return &types.RabbitMQMetrics{
		QueueName:     r.queueName,
		MessageCount:  queueInfo.Messages,
		ConsumerCount: queueInfo.Consumers,
		MessageRate:   queueInfo.MessagesDetails.Rate,
		Timestamp:     time.Now(),
	}, nil
}
