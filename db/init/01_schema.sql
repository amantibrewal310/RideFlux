-- RideFlux Database Schema
-- Executed on first docker compose up via entrypoint

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Riders
-- ============================================================
CREATE TABLE riders (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(120) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    phone       VARCHAR(20),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Drivers
-- ============================================================
CREATE TABLE drivers (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(120) NOT NULL,
    email         VARCHAR(255) NOT NULL UNIQUE,
    phone         VARCHAR(20),
    vehicle_type  VARCHAR(20) NOT NULL CHECK (vehicle_type IN ('auto','mini','sedan','suv')),
    status        VARCHAR(20) NOT NULL DEFAULT 'offline' CHECK (status IN ('available','busy','on_trip','offline')),
    current_lat   DOUBLE PRECISION,
    current_lng   DOUBLE PRECISION,
    rating        NUMERIC(3,2) DEFAULT 5.00,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_drivers_status ON drivers (status);
CREATE INDEX idx_drivers_location ON drivers (current_lat, current_lng) WHERE status = 'available';

-- ============================================================
-- Ride Requests
-- ============================================================
CREATE TABLE ride_requests (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rider_id          UUID NOT NULL REFERENCES riders(id),
    status            VARCHAR(30) NOT NULL DEFAULT 'pending'
                      CHECK (status IN (
                          'pending','matching','offered','accepted',
                          'driver_en_route','arrived','in_trip',
                          'completed','cancelled','no_drivers'
                      )),
    pickup_lat        DOUBLE PRECISION NOT NULL,
    pickup_lng        DOUBLE PRECISION NOT NULL,
    pickup_address    VARCHAR(500),
    dest_lat          DOUBLE PRECISION NOT NULL,
    dest_lng          DOUBLE PRECISION NOT NULL,
    dest_address      VARCHAR(500),
    vehicle_type      VARCHAR(20) NOT NULL CHECK (vehicle_type IN ('auto','mini','sedan','suv')),
    payment_method    VARCHAR(20) NOT NULL DEFAULT 'cash' CHECK (payment_method IN ('cash','card','wallet')),
    surge_multiplier  NUMERIC(4,2) NOT NULL DEFAULT 1.00,
    estimated_fare    NUMERIC(10,2),
    matched_driver_id UUID REFERENCES drivers(id),
    idempotency_key   VARCHAR(255) UNIQUE,
    offers_made       INT NOT NULL DEFAULT 0,
    max_offers        INT NOT NULL DEFAULT 3,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rides_status ON ride_requests (status);
CREATE INDEX idx_rides_rider ON ride_requests (rider_id);
CREATE INDEX idx_rides_idempotency ON ride_requests (idempotency_key) WHERE idempotency_key IS NOT NULL;

-- ============================================================
-- Ride Offers
-- ============================================================
CREATE TABLE ride_offers (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ride_id     UUID NOT NULL REFERENCES ride_requests(id),
    driver_id   UUID NOT NULL REFERENCES drivers(id),
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','accepted','declined','expired')),
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (ride_id, driver_id)
);

CREATE INDEX idx_offers_ride ON ride_offers (ride_id);

-- ============================================================
-- Trips
-- ============================================================
CREATE TABLE trips (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ride_id           UUID NOT NULL UNIQUE REFERENCES ride_requests(id),
    driver_id         UUID NOT NULL REFERENCES drivers(id),
    rider_id          UUID NOT NULL REFERENCES riders(id),
    status            VARCHAR(20) NOT NULL DEFAULT 'started'
                      CHECK (status IN ('started','in_progress','paused','completed','cancelled')),
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at      TIMESTAMPTZ,
    distance_m        INT DEFAULT 0,
    duration_s        INT DEFAULT 0,
    base_fare         NUMERIC(10,2) DEFAULT 0,
    distance_fare     NUMERIC(10,2) DEFAULT 0,
    time_fare         NUMERIC(10,2) DEFAULT 0,
    surge_multiplier  NUMERIC(4,2) DEFAULT 1.00,
    total_fare        NUMERIC(10,2) DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_trips_driver ON trips (driver_id);
CREATE INDEX idx_trips_rider ON trips (rider_id);

-- ============================================================
-- Payments
-- ============================================================
CREATE TABLE payments (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id            UUID NOT NULL REFERENCES trips(id),
    rider_id           UUID NOT NULL REFERENCES riders(id),
    amount             NUMERIC(10,2) NOT NULL,
    payment_method     VARCHAR(20) NOT NULL CHECK (payment_method IN ('cash','card','wallet')),
    status             VARCHAR(20) NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending','processing','succeeded','failed','refunded')),
    idempotency_key    VARCHAR(255) UNIQUE,
    psp_transaction_id VARCHAR(255),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_payments_trip ON payments (trip_id);
CREATE INDEX idx_payments_status ON payments (status);

-- ============================================================
-- Idempotency Keys
-- ============================================================
CREATE TABLE idempotency_keys (
    id             BIGSERIAL PRIMARY KEY,
    key            VARCHAR(255) NOT NULL,
    endpoint       VARCHAR(255) NOT NULL,
    response_code  INT NOT NULL,
    response_body  JSONB,
    expires_at     TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '24 hours',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (key, endpoint)
);

-- ============================================================
-- Seed Data: Bangalore-area drivers and a test rider
-- ============================================================
INSERT INTO riders (id, name, email, phone) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'Test Rider', 'rider@test.com', '+919999900001');

INSERT INTO drivers (id, name, email, phone, vehicle_type, status, current_lat, current_lng, rating) VALUES
    ('d0000000-0000-0000-0000-000000000001', 'Amit Kumar',   'amit@test.com',   '+919999900011', 'auto',  'available', 12.9716, 77.5946, 4.80),
    ('d0000000-0000-0000-0000-000000000002', 'Priya Singh',  'priya@test.com',  '+919999900012', 'mini',  'available', 12.9750, 77.5980, 4.90),
    ('d0000000-0000-0000-0000-000000000003', 'Rahul Sharma', 'rahul@test.com',  '+919999900013', 'sedan', 'available', 12.9680, 77.6000, 4.70),
    ('d0000000-0000-0000-0000-000000000004', 'Neha Gupta',   'neha@test.com',   '+919999900014', 'suv',   'available', 12.9780, 77.5900, 4.85),
    ('d0000000-0000-0000-0000-000000000005', 'Vikram Patel', 'vikram@test.com', '+919999900015', 'mini',  'offline',   12.9730, 77.6050, 4.60);
