# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

ARG REACT_APP_API_URL=http://localhost:8080

ENV REACT_APP_API_URL=$REACT_APP_API_URL

RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

RUN npm install -g serve@14

COPY --from=builder /app/build ./build

EXPOSE 3000

USER node

CMD ["serve", "-s", "build", "-l", "3000"]
