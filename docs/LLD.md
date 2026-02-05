# RideFlux - Low Level Design

## 1. Database Schema

### 1.1 Entity Relationship

```
riders 1──────M ride_requests M──────1 drivers
                    │
                    │ 1
                    │
               ride_offers M──────1 drivers
                    │
                    │ 1
                    │
                  trips 1──────M payments
```

### 1.2 Table Definitions

#### riders
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid_generate_v4() |
| name | VARCHAR(120) | NOT NULL |
| email | VARCHAR(255) | NOT NULL, UNIQUE |
| phone | VARCHAR(20) | |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |

#### drivers
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid_generate_v4() |
| name | VARCHAR(120) | NOT NULL |
| email | VARCHAR(255) | NOT NULL, UNIQUE |
| phone | VARCHAR(20) | |
| vehicle_type | VARCHAR(20) | NOT NULL, CHECK IN (auto, mini, sedan, suv) |
| status | VARCHAR(20) | NOT NULL, default 'offline', CHECK IN (available, busy, on_trip, offline) |
| current_lat | DOUBLE PRECISION | |
| current_lng | DOUBLE PRECISION | |
| rating | NUMERIC(3,2) | default 5.00 |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** `idx_drivers_status(status)`, `idx_drivers_location(current_lat, current_lng) WHERE status = 'available'`

#### ride_requests
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| rider_id | UUID | FK riders(id), NOT NULL |
| status | VARCHAR(30) | NOT NULL, CHECK IN (10 states) |
| pickup_lat/lng | DOUBLE PRECISION | NOT NULL |
| pickup_address | VARCHAR(500) | |
| dest_lat/lng | DOUBLE PRECISION | NOT NULL |
| dest_address | VARCHAR(500) | |
| vehicle_type | VARCHAR(20) | NOT NULL |
| payment_method | VARCHAR(20) | NOT NULL, default 'cash' |
| surge_multiplier | NUMERIC(4,2) | NOT NULL, default 1.00 |
| estimated_fare | NUMERIC(10,2) | |
| matched_driver_id | UUID | FK drivers(id) |
| idempotency_key | VARCHAR(255) | UNIQUE |
| offers_made | INT | NOT NULL, default 0 |
| max_offers | INT | NOT NULL, default 3 |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** `idx_rides_status`, `idx_rides_rider`, `idx_rides_idempotency`

#### ride_offers
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| ride_id | UUID | FK ride_requests(id), NOT NULL |
| driver_id | UUID | FK drivers(id), NOT NULL |
| status | VARCHAR(20) | NOT NULL, CHECK IN (pending, accepted, declined, expired) |
| expires_at | TIMESTAMPTZ | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Constraints:** UNIQUE(ride_id, driver_id). **Indexes:** `idx_offers_ride`

#### trips
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| ride_id | UUID | FK ride_requests(id), UNIQUE, NOT NULL |
| driver_id | UUID | FK drivers(id), NOT NULL |
| rider_id | UUID | FK riders(id), NOT NULL |
| status | VARCHAR(20) | CHECK IN (started, in_progress, paused, completed, cancelled) |
| started_at | TIMESTAMPTZ | NOT NULL |
| completed_at | TIMESTAMPTZ | |
| distance_m | INT | default 0 |
| duration_s | INT | default 0 |
| base_fare | NUMERIC(10,2) | |
| distance_fare | NUMERIC(10,2) | |
| time_fare | NUMERIC(10,2) | |
| surge_multiplier | NUMERIC(4,2) | default 1.00 |
| total_fare | NUMERIC(10,2) | |

**Indexes:** `idx_trips_driver`, `idx_trips_rider`

#### payments
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| trip_id | UUID | FK trips(id), NOT NULL |
| rider_id | UUID | FK riders(id), NOT NULL |
| amount | NUMERIC(10,2) | NOT NULL |
| payment_method | VARCHAR(20) | NOT NULL |
| status | VARCHAR(20) | CHECK IN (pending, processing, succeeded, failed, refunded) |
| idempotency_key | VARCHAR(255) | UNIQUE |
| psp_transaction_id | VARCHAR(255) | |

**Indexes:** `idx_payments_trip`, `idx_payments_status`

#### idempotency_keys
| Column | Type | Constraints |
|--------|------|-------------|
| id | BIGSERIAL | PK |
| key | VARCHAR(255) | NOT NULL |
| endpoint | VARCHAR(255) | NOT NULL |
| response_code | INT | NOT NULL |
| response_body | JSONB | |
| expires_at | TIMESTAMPTZ | default now() + 24h |

**Constraints:** UNIQUE(key, endpoint)

---

## 2. API Specifications

### 2.1 REST Endpoints

#### POST /v1/rides
Create a new ride request.

**Headers:** `Idempotency-Key` (optional)

**Request:**
```json
{
  "rider_id": "uuid",
  "pickup_lat": 28.6139,
  "pickup_lng": 77.2090,
  "pickup_address": "Connaught Place, Delhi",
  "dest_lat": 28.5355,
  "dest_lng": 77.3910,
  "dest_address": "Noida Sector 62",
  "vehicle_type": "sedan",
  "payment_method": "cash"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "rider_id": "uuid",
  "status": "matching",
  "pickup_lat": 28.6139,
  "pickup_lng": 77.2090,
  "vehicle_type": "sedan",
  "surge_multiplier": 1.2,
  "estimated_fare": 245.00,
  "matched_driver_id": null,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### GET /v1/rides/{id}
Returns ride details with current status.

#### POST /v1/drivers/{id}/location
**Request:** `{"lat": 28.6139, "lng": 77.2090}`

Updates driver location in both PostgreSQL and Redis GEO index.

#### POST /v1/drivers/{id}/accept
**Request:** `{"ride_id": "uuid", "accept": true}`

Accepts or declines a ride offer. Uses `SELECT FOR UPDATE` to prevent double-accept.

**Error cases:**
- 409: No pending offer, or offer already accepted by another driver
- 404: Ride not found

#### POST /v1/trips/{id}/end
**Request:** `{"distance_m": 12500, "duration_s": 1800}`

Calculates final fare and completes the trip.

#### POST /v1/payments
**Headers:** `Idempotency-Key` (required)

**Request:** `{"trip_id": "uuid", "payment_method": "cash"}`

---

## 3. State Machines

### 3.1 Ride Request FSM

```
                                    ┌──────────┐
                                    │ cancelled │
                                    └──────────┘
                                         ▲
            cancel from any              │
            pre-trip state ──────────────┤
                                         │
┌─────────┐    ┌──────────┐    ┌─────────┴┐    ┌──────────┐
│ pending  │───▶│ matching │───▶│ offered  │───▶│ accepted │
└─────────┘    └──────────┘    └──────────┘    └──────────┘
                    ▲               │  │              │
                    │    decline/   │  │              ▼
                    └───expire──────┘  │     ┌────────────────┐
                                       │     │ driver_en_route│
                                       ▼     └────────────────┘
                                 ┌────────────┐       │
                                 │ no_drivers  │       ▼
                                 └────────────┘  ┌──────────┐
                                                 │ arrived  │
                                                 └──────────┘
                                                      │
                                                      ▼
                                                 ┌──────────┐
                                                 │ in_trip  │
                                                 └──────────┘
                                                      │
                                                      ▼
                                                 ┌──────────┐
                                                 │ completed│
                                                 └──────────┘
```

### 3.2 Ride Offer FSM
```
┌─────────┐───▶ accepted
│ pending │───▶ declined
└─────────┘───▶ expired
```

### 3.3 Trip FSM
```
┌─────────┐    ┌─────────────┐    ┌───────────┐
│ started │───▶│ in_progress │───▶│ completed │
└─────────┘    └─────────────┘    └───────────┘
                    │    ▲
                    ▼    │ resume
                ┌────────┐
                │ paused │
                └────────┘

Cancel from: started, in_progress, paused → cancelled
```

---

## 4. Caching Strategy

### 4.1 Redis Key Layout

| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `drivers:geo:{vehicle_type}` | GEO | - | Spatial index for driver matching |
| `drivers:lastping:{driver_id}` | STRING | 30s | Driver heartbeat / liveness |
| `ride:{ride_id}` | STRING (JSON) | 5min | Ride data cache |
| `surge:demand:{zone}` | STRING (counter) | 5min | Demand counter per zone |
| `surge:multiplier:{zone}` | STRING | 2min | Computed surge multiplier |
| `offer_expiry_queue` | SORTED SET | - | Offer IDs scored by expiry timestamp |
| `ratelimit:{ip}` | SORTED SET | 60s | Sliding window rate limiter |
| `idemp:{key}:{endpoint}` | STRING (JSON) | 1h | Idempotency response cache |

### 4.2 Cache Invalidation
- Ride cache invalidated on every status change
- Driver GEO entry removed when driver goes offline
- Idempotency keys expire after 1h (Redis) / 24h (DB)

---

## 5. Concurrency Control

### 5.1 Driver Matching
```sql
SELECT * FROM drivers
WHERE id = $1 AND status = 'available'
FOR UPDATE SKIP LOCKED;
```
- `FOR UPDATE` acquires a row-level lock
- `SKIP LOCKED` prevents waiting — if another transaction is matching the same driver, the row is skipped
- Combined with Redis GEO filtering, this gives near-zero contention matching

### 5.2 Offer Acceptance
```sql
SELECT * FROM ride_offers
WHERE ride_id = $1 AND driver_id = $2 AND status = 'pending'
FOR UPDATE;
```
- Prevents double-accept race condition
- Second concurrent accept gets 409 Conflict

---

## 6. Fare Calculation

```python
FARE_CONFIG = {
    "auto":  {"base": 25, "per_km": 8,  "per_min": 1.0, "min_fare": 30},
    "mini":  {"base": 40, "per_km": 10, "per_min": 1.5, "min_fare": 50},
    "sedan": {"base": 60, "per_km": 14, "per_min": 2.0, "min_fare": 80},
    "suv":   {"base": 80, "per_km": 18, "per_min": 2.5, "min_fare": 100},
}

subtotal = base + (distance_km × per_km) + (duration_min × per_min)
surge_amount = subtotal × (surge_multiplier - 1)
total = max(subtotal + surge_amount, min_fare)
```

---

## 7. Surge Pricing Algorithm

1. **Zone grid:** Map is divided into ~1km cells using `floor(lat / 0.01) × 0.01`
2. **Demand tracking:** Each ride request increments `surge:demand:{zone}` (5min TTL)
3. **Supply counting:** `GEOSEARCH` counts available drivers within 3km of pickup
4. **Formula:** `ratio = demand / supply`, `multiplier = min(1.0 + (ratio - 1) × 0.5, 3.0)`
5. **Caching:** Computed multiplier cached for 2 minutes per zone

---

## 8. Idempotency

### Two-level check:
1. **Redis fast-path:** `GET idemp:{key}:{endpoint}` (1h TTL) — sub-millisecond
2. **DB fallback:** Query `idempotency_keys` table (24h retention) — if Redis evicted
3. **Write path:** Idempotency record stored in same DB transaction as main operation
4. **Redis write-through:** After DB commit, cache response in Redis

### Applied to:
- `POST /v1/rides` — prevents duplicate ride creation
- `POST /v1/payments` — prevents double-charging

---

## 9. WebSocket Events

| Event | Channel | Payload |
|-------|---------|---------|
| `ride:requested` | dashboard | ride_id, pickup, dest, vehicle_type, surge, fare |
| `ride:offered` | dashboard, ride:{id} | ride_id, driver_id, offer_id, expires_at |
| `ride:matched` | dashboard, ride:{id} | ride_id, driver_id, driver_name, driver_lat/lng |
| `ride:started` | dashboard, ride:{id} | ride_id, trip_id |
| `ride:completed` | dashboard, ride:{id} | ride_id, trip_id, fare breakdown |
| `ride:cancelled` | dashboard, ride:{id} | ride_id, reason |
| `ride:no_drivers` | dashboard, ride:{id} | ride_id, reason |
| `driver:location_update` | dashboard | driver_id, lat, lng, vehicle_type, status |
| `driver:status_changed` | dashboard | driver_id, old_status, new_status |

---

## 10. Monitoring (New Relic)

### Custom Events
| Event | Attributes |
|-------|-----------|
| `DriverMatching` | duration_ms, radius_km, found (bool), vehicle_type |
| `FareCalculation` | vehicle_type, distance_km, duration_min, surge, total |
| `SurgeComputed` | zone, demand, supply, multiplier |

### Alerts
| Condition | Threshold |
|-----------|-----------|
| API p95 latency | > 500ms |
| Matching duration p95 | > 800ms |
| Error rate | > 1% |
| Payment failure rate | > 5% |
