FROM golang:1.25-alpine AS builder

WORKDIR /app

COPY main.go .

RUN go mod init consumer && \
    go get github.com/streadway/amqp && \
    CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o consumer main.go

FROM alpine:3.21

RUN apk add --no-cache ca-certificates && \
    addgroup -S app && adduser -S app -G app

WORKDIR /app

COPY --from=builder /app/consumer .

RUN chown app:app consumer

USER app

CMD ["./consumer"]
