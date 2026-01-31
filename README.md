# Real-time Collaborative Document Editor

A web-based collaborative document editing tool built with FastAPI, MongoDB, Redis, and Docker Swarm.

## Features

- **Real-time Sync**: WebSockets + Redis Pub/Sub for cross-replica synchronization
- **Conflict Resolution**: CRDTs/OT logic for handling concurrent edits
- **User Presence**: Real-time online status and cursor position tracking
- **Versioning**: Automated snapshots and rollback in MongoDB

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: MongoDB (motor async driver)
- **Cache/Pub-Sub**: Redis
- **Infrastructure**: Docker Swarm, Traefik
- **Package Manager**: uv
- **Linting**: Ruff

## Quick Start

### Prerequisites

- Docker & Docker Compose
- uv (Python package manager)

### Local Development

```bash
# Start all services
make up

# View logs
make logs

# Run with debugger (port 5678)
make debug

# Stop services
make down
```

### Available Commands

| Command | Description |
|---------|-------------|
| `make up` | Start local development stack |
| `make down` | Stop local stack |
| `make build` | Build Docker images |
| `make logs` | View container logs |
| `make debug` | Start with debugpy enabled |
| `make shell` | Open shell in app container |
| `make lint` | Run Ruff linting |
| `make format` | Format code with Ruff |
| `make test` | Run pytest |

### Production Deployment

```bash
# Deploy to Docker Swarm
make prod-deploy

# View production logs
make prod-logs
```

## Project Structure

```
├── src/
│   ├── main.py              # FastAPI entry point
│   ├── core/                # Core utilities (config, database, etc.)
│   └── modules/             # Feature modules (auth, documents, etc.)
├── config/envs/             # Environment configurations
├── infrastructure/          # Docker & deployment files
│   ├── local/               # Local development
│   └── prod/                # Production (Swarm + Traefik)
└── tests/                   # Shared test utilities
```

## License

MIT
