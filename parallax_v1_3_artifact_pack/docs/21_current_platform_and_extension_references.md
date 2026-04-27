# 21 — Current Platform and Extension Reference Links

Implementation agents must verify platform and extension documentation again during coding. This file captures the reference posture used to prepare v1.3.

## Mobile location and radio context

- Apple Core Location archive: standard location, region monitoring, and significant-change services.
  - https://developer.apple.com/library/archive/documentation/UserExperience/Conceptual/LocationAwarenessPG/CoreLocation/CoreLocation.html
- Apple region monitoring and iBeacon archive.
  - https://developer.apple.com/library/archive/documentation/UserExperience/Conceptual/LocationAwarenessPG/RegionMonitoring/RegionMonitoring.html
- Apple energy guidance for location accuracy/duration.
  - https://developer.apple.com/library/archive/documentation/Performance/Conceptual/EnergyGuide-iOS/LocationBestPractices.html
- Android Fused Location Provider.
  - https://developers.google.com/location-context/fused-location-provider
- Android last-known location.
  - https://developer.android.com/develop/sensors-and-location/location/retrieve-current
- Android background location and battery guidance.
  - https://developer.android.com/develop/sensors-and-location/location/battery
- Android Wi-Fi scanning.
  - https://developer.android.com/develop/connectivity/wifi/wifi-scan
- Android nearby Wi-Fi devices permission.
  - https://developer.android.com/develop/connectivity/wifi/wifi-permissions
- Android Bluetooth permissions.
  - https://developer.android.com/develop/connectivity/bluetooth/bt-permissions
- Android Wi-Fi Aware.
  - https://developer.android.com/develop/connectivity/wifi/wifi-aware

## Database/search/analytics extensions

- TimescaleDB/Tiger Data `create_hypertable`.
  - https://www.tigerdata.com/docs/reference/timescaledb/hypertables/create_hypertable
- Tiger Data approximate percentile guidance for continuous aggregates.
  - https://www.tigerdata.com/docs/use-timescale/latest/hyperfunctions/percentile-approx/approximate-percentile
- Tiger Data `tdigest`/two-step aggregate guidance.
  - https://www.tigerdata.com/docs/api/latest/hyperfunctions/percentile-approximation/tdigest
- pgvector HNSW examples.
  - https://github.com/pgvector/pgvector
- ParadeDB BM25 index syntax.
  - https://docs.paradedb.com/documentation/indexing/create-index
- PostGIS `ST_DWithin`.
  - https://postgis.net/docs/ST_DWithin.html

## Implementation note

The artifact pack intentionally keeps PostGIS, ParadeDB, pgvector, and TimescaleDB behind optional profiles or feature gates where possible. Extension-only SQL lives under `database/optional_profiles/`; the core timing app must work on baseline PostgreSQL with pgcrypto/citext and without mobile sensor permissions.
