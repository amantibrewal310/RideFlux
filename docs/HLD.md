# RideFlux - High Level Design

## 1. System Overview

RideFlux is a real-time ride-hailing platform that connects riders with drivers. The system handles ride requests, driver matching, trip lifecycle management, fare calculation, and payment processing with real-time updates delivered via WebSockets.

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Dashboard │  │ Rides    │  │ Drivers  │  │ Leaflet Map   │  │
│  │ Page     │  │ Page     │  │ Page     │  │ (OpenStreetMap)│  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬───────┘  │
│       │              │              │                │          │
│  ┌────▼──────────────▼──────────────▼────────────────▼───────┐  │
│  │  Zustand Stores (Rides, Drivers, Notifications)           │  │
│  └──────────────────────┬────────────────────────────────────┘  │
│                         │                                       │
│  ┌──────────────────────▼────────────────────────────────────┐  │
│  │  API Client (REST)  │  WebSocket Client (auto-reconnect)  │  │
│  └──────────┬──────────┘──────────────┬──────────────────────┘  │
└─────────────┼─────────────────────────┼─────────────────────────┘
              │ HTTP                     │ WS
              ▼                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  REST API (/v1)  │  │  WebSocket (/ws) │                    │
│  │  - rides         │  │  - dashboard     │                    │
│  │  - drivers       │  │  - rides/{id}    │                    │
│  │  - trips         │  └────────┬─────────┘                    │
│  │  - payments      │           │                              │
│  │  - health        │  ┌────────▼─────────┐                    │
│  └────────┬─────────┘  │ ConnectionManager│                    │
│           │            │ (channel-based)  │                    │
│  ┌────────▼────────────┴──────────────────────────────────┐    │
│  │              Service Layer                              │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │ Ride     │ │ Matching │ │ Trip     │ │ Payment  │  │    │
│  │  │ Service  │ │ Service  │ │ Service  │ │ Service  │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐   │    │
│  │  │ Surge    │ │ Driver   │ │ Notification Service │   │    │
│  │  │ Service  │ │ Service  │ └──────────────────────┘   │    │
│  │  └──────────┘ └──────────┘                            │    │
│  └────────────────────────────────────────────────────────┘    │
│           │                        │                           │
│  ┌────────▼──────────┐   ┌────────▼──────────┐                │
│  │  State Machines   │   │   Cache Layer     │                │
│  │  - Ride FSM       │   │  - Driver Geo     │                │
│  │  - Offer FSM      │   │  - Ride Cache     │                │
│  │  - Trip FSM       │   └────────┬──────────┘                │
│  └───────────────────┘            │                            │
└───────────────────────────────────┼────────────────────────────┘
              │                     │
              ▼                     ▼
┌──────────────────────┐  ┌──────────────────────┐
│  PostgreSQL 15       │  │  Redis 7             │
│  - riders            │  │  - Driver GEO index  │
│  - drivers           │  │  - Heartbeats        │
│  - ride_requests     │  │  - Surge counters    │
│  - ride_offers       │  │  - Ride cache        │
│  - trips             │  │  - Rate limiting     │
│  - payments          │  │  - Idempotency cache │
│  - idempotency_keys  │  │  - Offer expiry queue│
└──────────────────────┘  └──────────────────────┘
```

## 3. Component Overview

### 3.1 Frontend (React + TypeScript)
- **Single Page Application** built with Vite for fast dev/build
- **Zustand** for lightweight state management with Map-based stores for O(1) lookups
- **Leaflet** with OpenStreetMap tiles for real-time map visualization (no API key required)
- **WebSocket client** with auto-reconnect and exponential backoff

### 3.2 Backend (FastAPI)
- **Async Python** throughout (asyncio, asyncpg, aioredis)
- **Service layer pattern** separating business logic from API routes
- **State machines** enforcing valid lifecycle transitions for rides, offers, and trips
- **Background tasks** for offer expiry polling and surge recomputation

### 3.3 PostgreSQL
- Primary data store for all entities
- `SELECT FOR UPDATE SKIP LOCKED` for race-condition-free driver matching
- UUID primary keys for distributed-friendly IDs

### 3.4 Redis
- **GEO indexes** for spatial driver lookup (`GEOSEARCH`)
- **Sorted sets** for offer expiry queue
- **Key-value** for caching, rate limiting, idempotency, surge pricing

## 4. Key Data Flows

### 4.1 Ride Request Flow
```
Rider -> POST /v1/rides -> Surge calc -> Fare estimate -> Save ride (matching)
  -> Find nearby drivers (Redis GEO) -> Lock driver (FOR UPDATE SKIP LOCKED)
  -> Create offer (20s TTL) -> Notify driver (WebSocket)
  -> Driver accepts -> Ride status: accepted -> Trip begins
```

### 4.2 Real-Time Updates
```
State change in service -> NotificationService -> ConnectionManager
  -> Broadcast to ride:{id} channel + dashboard channel
  -> All subscribed WebSocket clients receive update
  -> Frontend Zustand store updates -> React re-renders
```

### 4.3 Payment Flow
```
Trip completes -> POST /v1/payments (with idempotency key)
  -> Validate trip completed -> Check idempotency (Redis -> DB)
  -> Create payment -> PSP mock call -> Update status
  -> Cache idempotency response
```

## 5. Non-Functional Requirements

| Aspect | Approach |
|--------|----------|
| **Scalability** | Stateless backend, Redis for shared state, connection-pool-friendly |
| **Reliability** | Idempotency on writes, state machines prevent invalid transitions |
| **Consistency** | `SELECT FOR UPDATE SKIP LOCKED` prevents double-booking drivers |
| **Observability** | New Relic APM with custom events for matching, fare, surge |
| **Performance** | Redis caching, imperative Leaflet marker updates, Map-based stores |

## 6. Infrastructure

All services run via Docker Compose:
- **postgres:15-alpine** with health checks and volume persistence
- **redis:7-alpine** with AOF persistence and password auth
- **backend** with hot-reload for development
- **frontend** with Vite dev server and API proxy
