# 20 — Mobile Location, Radio Context, and Privacy Reference

This document gives the implementation agent concrete direction for mobile context capture. It is not a substitute for checking current platform documentation during implementation, because platform permissions and APIs evolve.

## Platform signals to consider

### GPS / fused location

Use for:

- start/end place context;
- transition latency;
- place-aware estimates;
- anomaly detection when a timer crosses a meaningful place boundary.

Store:

- latitude/longitude only when user permits;
- horizontal accuracy;
- vertical accuracy if available;
- altitude if available and useful;
- speed/course if available and useful;
- provider/source;
- timestamp;
- staleness;
- permission state.

Default posture:

- use last-known or low-power location at event boundaries;
- avoid continuous location;
- degrade to coarse or user-selected place when precise location is not needed;
- store raw coordinates with a retention policy and allow deletion.

### Wi-Fi connected network / scan results

Use for:

- indoor/place hints;
- distinguishing home kitchen vs office vs garage when GPS is weak;
- detecting that a run occurred in the usual environment;
- optional radio fingerprint clustering.

Risks:

- SSID/BSSID can identify homes, workplaces, and movement patterns.
- Android permissions treat many Wi-Fi APIs as location-adjacent.
- Scan frequency can be throttled and should not be relied on for high-frequency timing.

Default posture:

- do not store raw BSSID/MAC by default;
- store salted per-user hash, RSSI bucket, and source timestamp;
- use `redacted_display_label` only for user-provided or explicitly redacted safe
  text; never store raw SSID/BSSID/MAC/beacon identifiers in that field;
- store raw details only as encrypted short-retention artifacts if the user enables advanced diagnostics;
- do not issue active scans repeatedly; prefer passive/available results.

### Wi-Fi RTT / FTM

Use for:

- optional indoor ranging where hardware/APs support it;
- advanced place calibration;
- not required for core app.

Default posture:

- optional, disabled by default;
- never block timing on RTT availability;
- store distance/accuracy, not raw AP identity unless policy allows.

### BLE / iBeacon / UWB

Use for:

- user-configured proximity anchors;
- room/workbench-specific capture;
- watch/accessory integration;
- optional NFC/beacon-assisted workflows.

Risks:

- BLE beacons can reveal precise places.
- Nearby-device permissions and location assertions differ by platform/version.
- UWB availability is limited and device-specific.

Default posture:

- user-configured anchors only;
- hashed identifiers by default;
- no blanket BLE scanning without a specific feature;
- no sensitive place label inference without confirmation.

### Motion/activity state

Use for:

- detecting likely transition time;
- identifying vehicle vs walking context;
- detecting forget-to-stop candidates;
- improving start-latency/transition models.

Default posture:

- store coarse state only;
- no raw accelerometer streams in backend;
- avoid high-frequency sensor upload;
- treat as low-confidence evidence.

### Device/app state

Use for:

- offline capture quality;
- possible forgot-to-stop detection;
- capture method analytics;
- explaining missing context.

Store:

- foreground/background/locked if available and allowed;
- battery/charging bucket;
- connectivity state;
- source device type;
- local/monotonic timestamp metadata.

Avoid:

- collecting foreground app names or sensitive OS-level activity unless explicitly justified and consented.

## Permission strategy

Ask for the smallest permission needed for the feature the user is actively enabling.
Before requesting or using an OS permission, fetch
`GET /v1/privacy/context-capture-policy` and confirm the corresponding server
policy flag is enabled. If the server policy disables a signal, the client must
not collect or upload that signal even if the OS permission is already granted.

Suggested ladder:

1. No location: core timing and manual place selection.
2. Approximate/coarse location: place-aware estimates and broad transition context.
3. Precise location while using app: event-boundary context and better place confirmation.
4. Background location: only for explicit user-enabled workflows such as geofence prompts or always-available run assistance.
5. Nearby/radio permissions: only for explicit indoor/place calibration, watch/accessory, or user-configured anchors.

Never bundle all permissions into first launch.

## Retention strategy

The retention defaults below are implemented through `context_capture_policy`
and per-observation `retention_policy` values. Per-run overrides may narrow
retention, but must not broaden it beyond the server policy.

| Data type | Default retention | Notes |
|---|---:|---|
| capture method and trigger | durable | low risk, useful for analytics |
| permission state | durable | needed for explaining missing context |
| coarse place category | durable after confirmation | not raw location |
| inferred place candidate | durable if confirmed; otherwise short TTL | prevent hidden profiling |
| precise lat/lon | short TTL or derived-only by default | user can opt in |
| Wi-Fi/BLE identifiers | salted hash only by default | raw only encrypted + short TTL |
| radio RSSI/distance | short TTL or aggregate | useful for clustering |
| motion state | durable coarse state | no raw streams |
| raw routes | disabled by default | not needed for alpha |
| sensitive/private place labels | user-confirmed only | extra privacy controls |

## Design language for location context

Use calm, transparent language:

- "Use approximate place to improve time estimates?"
- "Saved without location context."
- "This run looks unusual because the place changed."
- "Confirm place: Kitchen, Garage, or Somewhere else?"
- "Forget this place context for this run."

Avoid:

- "tracking";
- "surveillance";
- "BSSID";
- "radio fingerprint";
- "precise geolocation" in normal UI.

Advanced settings may expose technical details.

## Implementation acceptance criteria

- Timing works with all sensor permissions denied.
- A session can attach zero, one, or many context snapshots.
- Every observation includes source, timestamp, and confidence/accuracy.
- Place inference is user-scoped and correctable.
- Sensitive labels are never inferred without confirmation.
- Raw radio/location data can be redacted/deleted.
- Permission state is visible in debug/evidence views.
- Context never silently changes timing baselines.
