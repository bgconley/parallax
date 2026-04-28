from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .common import ApiModel, MutationEnvelope

PrivacyClass = Literal["normal", "sensitive", "private"]
AnnotationInputMode = Literal["text", "voice", "quick_chip", "system_detected", "review_note"]
AnnotationStatus = Literal[
    "captured",
    "transcription_pending",
    "transcribed",
    "extraction_pending",
    "extracted",
    "needs_confirmation",
    "confirmed",
    "corrected",
    "ignored",
    "redacted",
    "deleted",
]
CaptureMethod = Literal[
    "manual_timer_button",
    "lock_screen_widget",
    "home_screen_widget",
    "watch",
    "voice",
    "quick_chip",
    "shortcut",
    "nfc_tag",
    "calendar_import",
    "system_detected",
    "review_reconstruction",
    "background_signal",
    "api",
]
CaptureTrigger = Literal[
    "user_initiated",
    "timer_event",
    "annotation",
    "checkpoint_event",
    "permission_change",
    "geofence_transition",
    "place_visit",
    "radio_fingerprint_change",
    "motion_change",
    "sync_replay",
    "review",
]
GeospatialSourceType = Literal[
    "fused_location",
    "gps",
    "network_location",
    "wifi_derived",
    "wifi_rtt",
    "ble_beacon",
    "ibeacon",
    "uwb",
    "cell",
    "manual_place",
    "geofence",
    "visit",
    "significant_location_change",
    "none",
]
RadioSourceType = Literal[
    "wifi_connected_network",
    "wifi_scan",
    "wifi_rtt",
    "ble_scan",
    "ibeacon",
    "uwb",
    "cell",
    "unknown",
]
MotionState = Literal[
    "unknown",
    "stationary",
    "walking",
    "running",
    "cycling",
    "driving",
    "in_vehicle",
    "transit",
    "mixed",
]
PlaceCategory = Literal[
    "unknown",
    "home",
    "work",
    "office",
    "kitchen",
    "garage",
    "yard",
    "store",
    "gym",
    "vehicle",
    "public",
    "client_site",
    "medical",
    "school",
    "religious",
    "other",
]
SensorAvailabilityState = Literal[
    "available",
    "permission_denied",
    "disabled_by_user",
    "disabled_by_system",
    "unsupported",
    "unavailable",
    "not_requested",
    "stale",
]
SensorRetentionPolicy = Literal[
    "do_not_store",
    "derived_only",
    "short_ttl_raw",
    "store_with_consent",
]
TimingReviewFlagType = Literal[
    "possible_forgotten_timer",
    "place_transition",
    "long_idle_gap",
    "impossible_sequence",
    "low_context_quality",
    "privacy_review_required",
    "manual_review_requested",
    "other",
]
TimingReviewFlagStatus = Literal["open", "snoozed", "resolved", "dismissed"]
ReviewFlagSeverity = Literal["low", "medium", "high"]


class TemporalContextAnnotation(ApiModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    checkpoint_run_id: UUID | None = None
    input_mode: AnnotationInputMode
    raw_text: str | None = None
    redacted_text: str | None = None
    transcript_confidence: float | None = Field(default=None, ge=0, le=1)
    audio_object_ref: str | None = None
    timer_elapsed_seconds: int | None = Field(default=None, ge=0)
    timer_active_seconds: int | None = Field(default=None, ge=0)
    occurred_at: datetime
    privacy_class: PrivacyClass
    status: AnnotationStatus
    client_mutation_id: str
    client_device_id: str
    idempotency_key: str
    capture_context_snapshot_id: UUID | None = None
    capture_context_snapshot_ref: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class CreateAnnotationRequest(ApiModel):
    mutation: MutationEnvelope
    checkpoint_run_id: UUID | None = None
    input_mode: AnnotationInputMode
    raw_text: str | None = None
    audio_object_ref: str | None = None
    timer_elapsed_seconds: int | None = Field(default=None, ge=0)
    timer_active_seconds: int | None = Field(default=None, ge=0)
    capture_context_snapshot_id: UUID | None = None
    capture_context_snapshot_ref: str | None = None
    occurred_at: datetime
    privacy_class: PrivacyClass = "normal"
    metadata: dict[str, object] = Field(default_factory=dict)


class ContextCapturePolicy(ApiModel):
    id: UUID
    user_id: UUID
    location_enabled: bool
    precise_location_enabled: bool
    background_location_enabled: bool
    radio_context_enabled: bool
    motion_context_enabled: bool
    device_context_enabled: bool
    raw_location_retention_days: int | None = Field(default=None, ge=0)
    raw_radio_retention_days: int | None = Field(default=None, ge=0)
    default_location_retention_policy: SensorRetentionPolicy
    default_radio_retention_policy: SensorRetentionPolicy
    per_run_context_default: bool
    updated_at: datetime
    created_at: datetime


class UpdateContextCapturePolicyRequest(ApiModel):
    mutation: MutationEnvelope
    location_enabled: bool | None = None
    precise_location_enabled: bool | None = None
    background_location_enabled: bool | None = None
    radio_context_enabled: bool | None = None
    motion_context_enabled: bool | None = None
    device_context_enabled: bool | None = None
    raw_location_retention_days: int | None = Field(default=None, ge=0)
    raw_radio_retention_days: int | None = Field(default=None, ge=0)
    default_location_retention_policy: SensorRetentionPolicy | None = None
    default_radio_retention_policy: SensorRetentionPolicy | None = None
    per_run_context_default: bool | None = None


class UserPlace(ApiModel):
    id: UUID
    user_id: UUID
    display_name: str
    category: PlaceCategory
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_meters: int | None = Field(default=None, ge=1)
    source: GeospatialSourceType
    privacy_class: PrivacyClass
    confirmed_by_user: bool
    is_sensitive: bool
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CreatePlaceRequest(ApiModel):
    mutation: MutationEnvelope
    display_name: str = Field(min_length=1)
    category: PlaceCategory
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_meters: int | None = Field(default=None, ge=1)
    source: GeospatialSourceType
    privacy_class: PrivacyClass
    confirmed_by_user: bool = True
    is_sensitive: bool = False
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class UpdatePlaceRequest(ApiModel):
    mutation: MutationEnvelope
    display_name: str | None = None
    category: PlaceCategory | None = None
    radius_meters: int | None = Field(default=None, ge=1)
    privacy_class: PrivacyClass | None = None
    confirmed_by_user: bool | None = None
    is_sensitive: bool | None = None
    aliases: list[str] | None = None


class ResolvePlaceRequest(ApiModel):
    snapshot_id: UUID | None = None
    candidate_label: str | None = None
    candidate_category: PlaceCategory
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_meters: int | None = Field(default=None, ge=1)
    include_unconfirmed_candidates: bool = False
    existing_place_id: UUID | None = None
    privacy_class: PrivacyClass


class ResolvePlaceCandidate(ApiModel):
    place: UserPlace | None = None
    candidate_label: str | None = None
    candidate_category: PlaceCategory
    confidence: float = Field(ge=0, le=1)
    match_type: Literal["existing_place", "inferred_candidate", "manual_candidate", "no_match"]
    evidence: dict[str, object] = Field(default_factory=dict)


class ResolvePlaceResponse(ApiModel):
    candidates: list[ResolvePlaceCandidate]
    recommended_place_id: UUID | None = None
    requires_confirmation: bool


class GeospatialObservationInput(ApiModel):
    source: GeospatialSourceType
    observed_at: datetime
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    altitude_meters: float | None = None
    horizontal_accuracy_meters: float | None = Field(default=None, ge=0)
    vertical_accuracy_meters: float | None = Field(default=None, ge=0)
    speed_mps: float | None = None
    course_degrees: float | None = Field(default=None, ge=0, le=360)
    is_precise: bool
    is_stale: bool
    staleness_seconds: int | None = Field(default=None, ge=0)
    privacy_class: PrivacyClass
    retention_policy: SensorRetentionPolicy
    metadata: dict[str, object] = Field(default_factory=dict)


class GeospatialObservation(GeospatialObservationInput):
    id: UUID
    user_id: UUID
    snapshot_id: UUID
    created_at: datetime


class RadioObservationInput(ApiModel):
    source: RadioSourceType
    observed_at: datetime
    identifier_hash: str | None = None
    label_hash: str | None = None
    redacted_display_label: str | None = None
    rssi_dbm: int | None = None
    tx_power_dbm: int | None = None
    distance_meters: float | None = Field(default=None, ge=0)
    distance_accuracy_meters: float | None = Field(default=None, ge=0)
    frequency_mhz: int | None = None
    channel: str | None = None
    is_connected: bool | None = None
    raw_encrypted_object_ref: str | None = None
    privacy_class: PrivacyClass
    retention_policy: SensorRetentionPolicy
    metadata: dict[str, object] = Field(default_factory=dict)


class RadioObservation(RadioObservationInput):
    id: UUID
    user_id: UUID
    snapshot_id: UUID
    created_at: datetime


class DeviceContextObservationInput(ApiModel):
    observed_at: datetime
    motion_state: MotionState
    battery_percent: int | None = Field(default=None, ge=0, le=100)
    charging_state: Literal["charging", "discharging", "full", "unknown"]
    network_state: Literal["offline", "wifi", "cellular", "ethernet", "mixed", "unknown"]
    device_type: Literal["phone", "tablet", "watch", "desktop", "browser", "unknown"]
    app_foreground_state: Literal["foreground", "background", "locked", "extension", "unknown"]
    privacy_class: PrivacyClass
    retention_policy: SensorRetentionPolicy
    metadata: dict[str, object] = Field(default_factory=dict)


class DeviceContextObservation(DeviceContextObservationInput):
    id: UUID
    user_id: UUID
    snapshot_id: UUID
    created_at: datetime


class InferredPlaceObservation(ApiModel):
    id: UUID
    user_id: UUID
    snapshot_id: UUID
    user_place_id: UUID | None = None
    candidate_label: str | None = None
    candidate_category: PlaceCategory
    confidence: float = Field(ge=0, le=1)
    confirmation_state: Literal[
        "auto_logged",
        "needs_confirmation",
        "confirmed",
        "corrected",
        "ignored",
        "deferred_to_review",
    ]
    evidence: dict[str, object]
    sensitive_label_detected: bool
    confirmed_at: datetime | None = None
    created_at: datetime


class CaptureContextSnapshot(ApiModel):
    id: UUID
    user_id: UUID
    session_id: UUID | None = None
    checkpoint_run_id: UUID | None = None
    user_place_id: UUID | None = None
    capture_method: CaptureMethod
    capture_trigger: CaptureTrigger
    client_captured_at: datetime
    server_received_at: datetime
    client_monotonic_millis: int | None = Field(default=None, ge=0)
    source_device_id: str
    app_foreground_state: Literal["foreground", "background", "locked", "extension", "unknown"]
    location_state: SensorAvailabilityState
    radio_state: SensorAvailabilityState
    motion_state_available: SensorAvailabilityState
    device_context_state: SensorAvailabilityState
    privacy_class: PrivacyClass
    retention_policy: SensorRetentionPolicy
    context_quality_score: float | None = Field(default=None, ge=0, le=1)
    permission_summary: dict[str, object]
    metadata: dict[str, object] = Field(default_factory=dict)
    geospatial_observations: list[GeospatialObservation] = Field(default_factory=list)
    radio_observations: list[RadioObservation] = Field(default_factory=list)
    device_context_observations: list[DeviceContextObservation] = Field(default_factory=list)
    inferred_places: list[InferredPlaceObservation] = Field(default_factory=list)
    client_mutation_id: str
    client_device_id: str
    idempotency_key: str
    created_at: datetime


class CreateCaptureContextSnapshotRequest(ApiModel):
    mutation: MutationEnvelope
    checkpoint_run_id: UUID | None = None
    user_place_id: UUID | None = None
    capture_method: CaptureMethod
    capture_trigger: CaptureTrigger
    client_captured_at: datetime
    client_monotonic_millis: int | None = Field(default=None, ge=0)
    source_device_id: str
    app_foreground_state: Literal["foreground", "background", "locked", "extension", "unknown"]
    location_state: SensorAvailabilityState
    radio_state: SensorAvailabilityState
    motion_state_available: SensorAvailabilityState
    device_context_state: SensorAvailabilityState
    privacy_class: PrivacyClass
    retention_policy: SensorRetentionPolicy
    context_quality_score: float | None = Field(default=None, ge=0, le=1)
    permission_summary: dict[str, object]
    geospatial_observations: list[GeospatialObservationInput] = Field(default_factory=list)
    radio_observations: list[RadioObservationInput] = Field(default_factory=list)
    device_context_observations: list[DeviceContextObservationInput] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class TimingReviewFlag(ApiModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    snapshot_id: UUID | None = None
    flag_type: TimingReviewFlagType
    status: TimingReviewFlagStatus
    severity: ReviewFlagSeverity
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason_code: str
    user_message: str
    evidence: dict[str, object]
    created_at: datetime
    resolved_at: datetime | None = None
    resolution_note: str | None = None


class UpdateTimingReviewFlagRequest(ApiModel):
    mutation: MutationEnvelope
    status: TimingReviewFlagStatus
    resolution_note: str | None = None
