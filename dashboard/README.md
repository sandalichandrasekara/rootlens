# Dashboard

> React frontend for real-time RootLens monitoring and RCA visualization.

## Quick Start

```bash
cd dashboard
npm install
cp .env.example .env.local  
npm start
# → http://localhost:3000
```

## Configuration

| Variable | Description |
|----------|-------------|
| `REACT_APP_API_URL` | RootLens API base URL (e.g. `http://localhost:8080`) |

Set in `.env.local` for development. Baked into the Docker image at build time for production.

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Home | `/` | System overview, status indicators |
| Live Metrics | `/metrics` | Real-time queue depth, consumers, pods — refreshes every 5s |
| RCA Analysis | `/rca` | Run analysis, view root cause + sub-cause + confidence |
| Workload Generator | `/workload` | Publish spike or sustained message load |

## Build

```bash
npm run build  
```

Docker:
```bash
docker build \
  --build-arg REACT_APP_API_URL=https://your-api-url \
  -f Dockerfile -t rootlens-dashboard .
docker run -p 3000:3000 rootlens-dashboard
```

## Stack

- React 19
- Recharts (metrics graphs)
- Served by `serve` on port 3000

## Project Structure

```
dashboard/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/          # Page-level components (Home, Dashboard, RCA, Workload)
│   ├── services/       # API client (api.js)
│   └── App.js          # Router + layout
├── public/
└── Dockerfile
```
