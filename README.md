# RideFlux

A scalable, low-latency ride-hailing platform with real-time driver location streaming, sub-second rider-driver matching, trip lifecycle management, surge pricing, and payment processing.

Built with FastAPI (async Python), React + TypeScript, PostgreSQL, and Redis. Includes a live-update dashboard with Leaflet maps for ride and fleet visibility.

---

## Architecture

```
Frontend (React + Zustand + Leaflet)
        │ REST + WebSocket
        ▼
Backend (FastAPI, async)
   ├── Service Layer (ride, matching, trip, payment, surge)
   ├── State Machines (ride, offer, trip FSMs)
   ├── Cache Layer (Redis GEO, ride cache)
   └── Middleware (rate limiter, idempotency)
        │                    │
        ▼                    ▼
   PostgreSQL 15         Redis 7
```

## Tech Stack

| Layer          | Technology                                                     |
| -------------- | -------------------------------------------------------------- |
| Backend        | Python 3.11, FastAPI, SQLAlchemy (async), asyncpg, Alembic     |
| Frontend       | React 18, TypeScript, Vite 5, Zustand, Leaflet + OpenStreetMap |
| Database       | PostgreSQL 15                                                  |
| Cache          | Redis 7 (GEO, sorted sets, key-value)                          |
| Real-time      | Native WebSockets (FastAPI + browser API)                      |
| Monitoring     | New Relic Python agent                                         |
| Infrastructure | Docker Compose                                                 |

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- (Optional) Python 3.11+, Node.js 20+ for local development without Docker

### 1. Clone and configure

```bash
git clone <repo-url> && cd RideFlux
cp .env.example .env
```

### 2. Start all services

```bash
docker compose up --build
```

This starts 4 services:

- **PostgreSQL** on port `5432` (auto-runs `db/init/01_schema.sql` with tables + seed data)
- **Redis** on port `6379`
- **Backend** on port `8000` (FastAPI with hot-reload)
- **Frontend** on port `5173` (Vite dev server)

### 3. Verify

```bash
# Health check
curl http://localhost:8000/health

# Open dashboard
open http://localhost:5173
```

---

## Local Development (without Docker)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set env vars (point to local Postgres + Redis)
export DATABASE_URL="postgresql+asyncpg://rideflux:rideflux_secret@localhost:5432/rideflux"
export REDIS_URL="redis://:redis_secret@localhost:6379/0"

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
cd backend
pip install aiosqlite  # needed for test SQLite backend

# Run all tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v
```

---

## API Endpoints

| Method | Endpoint                    | Description                     |
| ------ | --------------------------- | ------------------------------- |
| `GET`  | `/health`                   | Health check (Postgres + Redis) |
| `POST` | `/v1/rides`                 | Create ride request             |
| `GET`  | `/v1/rides`                 | List all rides                  |
| `GET`  | `/v1/rides/{id}`            | Get ride by ID                  |
| `POST` | `/v1/rides/{id}/cancel`     | Cancel a ride                   |
| `POST` | `/v1/drivers/{id}/location` | Update driver location          |
| `POST` | `/v1/drivers/{id}/accept`   | Accept/decline ride offer       |
| `GET`  | `/v1/drivers`               | List all drivers                |
| `GET`  | `/v1/drivers/{id}`          | Get driver by ID                |
| `POST` | `/v1/trips/{ride_id}/start` | Start a trip                    |
| `POST` | `/v1/trips/{id}/end`        | End trip + calculate fare       |
| `GET`  | `/v1/trips/{id}`            | Get trip by ID                  |
| `POST` | `/v1/payments`              | Process payment                 |

### WebSocket Endpoints

| Endpoint            | Description                              |
| ------------------- | ---------------------------------------- |
| `WS /ws/dashboard`  | All ride/driver events for the dashboard |
| `WS /ws/rides/{id}` | Ride-specific lifecycle events           |

---

## Example API Flow

```bash
# 1. Create a ride request
curl -X POST http://localhost:8000/v1/rides \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: ride-001" \
  -d '{
    "rider_id": "a0000000-0000-0000-0000-000000000001",
    "pickup_lat": 12.9716, "pickup_lng": 77.5946,
    "dest_lat": 12.9698, "dest_lng": 77.7500,
    "vehicle_type": "sedan", "payment_method": "cash"
  }'

# 2. Update driver location (triggers GEO index update)
curl -X POST http://localhost:8000/v1/drivers/d0000000-0000-0000-0000-000000000003/location \
  -H "Content-Type: application/json" \
  -d '{"lat": 12.9716, "lng": 77.5946}'

# 3. Driver accepts the ride offer
curl -X POST http://localhost:8000/v1/drivers/d0000000-0000-0000-0000-000000000003/accept \
  -H "Content-Type: application/json" \
  -d '{"ride_id": "<ride-id-from-step-1>", "accept": true}'

# 4. Start the trip
curl -X POST http://localhost:8000/v1/trips/<ride-id>/start

# 5. End the trip with distance/duration
curl -X POST http://localhost:8000/v1/trips/<trip-id>/end \
  -H "Content-Type: application/json" \
  -d '{"distance_m": 12500, "duration_s": 1800}'

# 6. Process payment
curl -X POST http://localhost:8000/v1/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: pay-001" \
  -d '{"trip_id": "<trip-id>", "payment_method": "cash"}'
```

---

## Key Features

### Driver Matching (Redis GEO)

- Spatial lookup via `GEOSEARCH` within 2km, expanding to 5km
- `SELECT FOR UPDATE SKIP LOCKED` prevents race conditions
- Offer expiry via Redis sorted set (20s TTL)
- Background task polls for expired offers every 1s

### Surge Pricing

- Zone-based demand tracking (~1km grid cells)
- Formula: `demand / supply` ratio mapped to 1.0x - 3.0x multiplier
- Cached per zone for 2 minutes

### Fare Calculation (INR)

| Vehicle | Base | Per km | Per min | Min Fare |
| ------- | ---- | ------ | ------- | -------- |
| Auto    | 25   | 8      | 1.0     | 30       |
| Mini    | 40   | 10     | 1.5     | 50       |
| Sedan   | 60   | 14     | 2.0     | 80       |
| SUV     | 80   | 18     | 2.5     | 100      |

### Idempotency

- `Idempotency-Key` header on POST endpoints
- Two-level check: Redis (1h TTL) -> DB (24h TTL)
- Prevents duplicate ride creation and double-charging

### State Machines

- **Ride**: 10 states (pending -> matching -> offered -> accepted -> driver_en_route -> arrived -> in_trip -> completed)
- **Offer**: 4 states (pending -> accepted/declined/expired)
- **Trip**: 5 states (started -> in_progress -> completed, with pause/resume)

---

## Project Structure

```
RideFlux/
├── docker-compose.yml
├── .env.example
├── db/init/01_schema.sql          # DDL + seed data
├── docs/
│   ├── HLD.md                     # High-level architecture
│   ├── LLD.md                     # Low-level design
│   └── IMPLEMENTATION_PLAN.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── newrelic.ini
│   ├── alembic.ini
│   ├── alembic/env.py
│   └── app/
│       ├── main.py                # FastAPI app, lifespan, middleware
│       ├── config.py              # Pydantic Settings
│       ├── database.py            # Async SQLAlchemy engine
│       ├── redis_client.py        # Redis connection pool
│       ├── models/                # 6 ORM models
│       ├── schemas/               # Pydantic request/response
│       ├── api/                   # REST routes (6 modules)
│       ├── ws/                    # WebSocket manager + handlers
│       ├── services/              # Business logic (7 services)
│       ├── state_machines/        # Ride, Offer, Trip FSMs
│       ├── cache/                 # Redis GEO + ride cache
│       ├── core/                  # Auth, exceptions, middleware
│       └── utils/                 # Haversine, fare calculation
├── backend/tests/
│   ├── conftest.py                # Fixtures (SQLite, fakeredis, httpx)
│   ├── unit/                      # FSM, fare, surge tests
│   └── integration/               # API endpoint tests
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── api/                   # REST + WebSocket clients
        ├── store/                 # Zustand (rides, drivers, notifications)
        ├── hooks/                 # useWebSocket, useDrivers
        ├── components/            # Layout, Map, Rides, Drivers, Common
        ├── pages/                 # Dashboard, Rides, Drivers
        ├── types/                 # TypeScript interfaces
        └── styles/globals.css     # Dark theme CSS
```

---

## Seed Data

The database is pre-loaded with test data on first startup:

**Test Rider:** `a0000000-0000-0000-0000-000000000001` (Test Rider, rider@test.com)

**Test Drivers (Bangalore area):**

| ID                        | Name         | Vehicle | Status    |
| ------------------------- | ------------ | ------- | --------- |
| d0000000-...-000000000001 | Amit Kumar   | auto    | available |
| d0000000-...-000000000002 | Priya Singh  | mini    | available |
| d0000000-...-000000000003 | Rahul Sharma | sedan   | available |
| d0000000-...-000000000004 | Neha Gupta   | suv     | available |
| d0000000-...-000000000005 | Vikram Patel | mini    | offline   |

---

## Documentation

- **[High-Level Design](docs/HLD.md)** - Architecture diagram, component overview, data flows
- **[Low-Level Design](docs/LLD.md)** - Database schema, API specs, state machines, caching strategy
