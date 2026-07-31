package utils

import (
	"fmt"
	"log"
	"time"
)

const timestampFormat = "2006-01-02 15:04:05"

type Logger struct {
	prefix string
}

func NewLogger(prefix string) *Logger {
	return &Logger{prefix: prefix}
}

func (l *Logger) Info(message string, args ...interface{}) {
	msg := fmt.Sprintf(message, args...)
	log.Printf("[%s] [INFO] [%s] %s", time.Now().Format(timestampFormat), l.prefix, msg)
}

func (l *Logger) Error(message string, args ...interface{}) {
	msg := fmt.Sprintf(message, args...)
	log.Printf("[%s] [ERROR] [%s] %s", time.Now().Format(timestampFormat), l.prefix, msg)
}

func (l *Logger) Debug(message string, args ...interface{}) {
	msg := fmt.Sprintf(message, args...)
	log.Printf("[%s] [DEBUG] [%s] %s", time.Now().Format(timestampFormat), l.prefix, msg)
}
