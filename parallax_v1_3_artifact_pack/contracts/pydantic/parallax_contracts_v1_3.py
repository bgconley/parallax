"""Pydantic-compatible core and context contracts for Parallax v1.3.

These models are implementation scaffolding only. Do not implement or generate
API behavior from this file alone. The OpenAPI contract and JSON Schema files
remain the complete source of truth; when this file differs, regenerate or patch
it from those canonical contracts before coding against it.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TimingMode(StrEnum):
    estimate_only = "estimate_only"
    whole_task = "whole_task"
    checkpointed = "checkpointed"
    routine = "routine"
    calibration = "calibration"
    passive = "passive"


class TimingSessionStatus(StrEnum):
    draft = "draft"
    intent_recorded = "intent_recorded"
    running = "running"
    paused = "paused"
    completed_unreviewed = "completed_unreviewed"
    reviewed = "reviewed"
    discarded = "discarded"
    abandoned = "abandoned"


class PrivacyClass(StrEnum):
    normal = "normal"
    sensitive = "sensitive"
    private = "private"


class TimingEventType(StrEnum):
    intent_recorded = "intent_recorded"
    session_started = "session_started"
    session_paused = "session_paused"
    session_resumed = "session_resumed"
    session_completed = "session_completed"
    session_abandoned = "session_abandoned"
    checkpoint_started = "checkpoint_started"
    checkpoint_completed = "checkpoint_completed"
    checkpoint_skipped = "checkpoint_skipped"
    annotation_captured = "annotation_captured"
    extracted_event_created = "extracted_event_created"
    active_work_started = "active_work_started"
    active_work_completed = "active_work_completed"
    setup_started = "setup_started"
    setup_completed = "setup_completed"
    resource_detour_started = "resource_detour_started"
    resource_detour_completed = "resource_detour_completed"
    interruption_started = "interruption_started"
    interruption_completed = "interruption_completed"
    waiting_started = "waiting_started"
    waiting_completed = "waiting_completed"
    side_quest_started = "side_quest_started"
    side_quest_completed = "side_quest_completed"
    transition_started = "transition_started"
    transition_completed = "transition_completed"
    bad_timer_marked = "bad_timer_marked"
    scope_changed = "scope_changed"
    user_correction_applied = "user_correction_applied"
    review_saved = "review_saved"
    sync_reconciled = "sync_reconciled"


class TemporalSpanType(StrEnum):
    active_work = "active_work"
    setup = "setup"
    resource_detour = "resource_detour"
    interruption = "interruption"
    waiting = "waiting"
    side_quest = "side_quest"
    start_latency = "start_latency"
    transition = "transition"
    body_energy = "body_energy"
    decision_loop = "decision_loop"
    attention_drift = "attention_drift"
    environment_friction = "environment_friction"
    bad_timer = "bad_timer"
    scope_change = "scope_change"
    other = "other"


class CountPolicy(StrEnum):
    wall_and_active = "wall_and_active"
    wall_only = "wall_only"
    active_only = "active_only"
    separate_start_latency = "separate_start_latency"
    separate_transition = "separate_transition"
    do_not_count = "do_not_count"
    review_required = "review_required"


class Severity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class TimingReviewFlagType(StrEnum):
    possible_forgotten_timer = "possible_forgotten_timer"
    place_transition = "place_transition"
    long_idle_gap = "long_idle_gap"
    impossible_sequence = "impossible_sequence"
    low_context_quality = "low_context_quality"
    privacy_review_required = "privacy_review_required"
    manual_review_requested = "manual_review_requested"
    other = "other"


class TimingReviewFlagStatus(StrEnum):
    open = "open"
    snoozed = "snoozed"
    resolved = "resolved"
    dismissed = "dismissed"


class ConfirmationState(StrEnum):
    auto_logged = "auto_logged"
    needs_confirmation = "needs_confirmation"
    confirmed = "confirmed"
    corrected = "corrected"
    ignored = "ignored"
    deferred_to_review = "deferred_to_review"


class MutationEnvelope(BaseModel):
    client_mutation_id: str
    client_device_id: str
    client_timestamp: datetime
    idempotency_key: str
    client_sequence: int | None = Field(default=None, ge=0)


class Activity(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    canonical_key: str | None = None
    description: str | None = None
    status: str = "active"
    merged_into_activity_id: UUID | None = None
    default_timing_mode: TimingMode = TimingMode.whole_task
    privacy_class: PrivacyClass = PrivacyClass.normal
    created_at: datetime
    updated_at: datetime


class ResolveActivityMatchType(StrEnum):
    canonical = "canonical"
    alias = "alias"
    fuzzy = "fuzzy"
    no_match = "no_match"


class ResolvedActivityCandidate(BaseModel):
    activity: Activity | None = None
    display_name: str
    confidence: float = Field(ge=0, le=1)
    match_type: ResolveActivityMatchType
    evidence: dict[str, Any] = Field(default_factory=dict)


class ResolveActivityResponse(BaseModel):
    candidates: list[ResolvedActivityCandidate]
    recommended_activity_id: UUID | None = None
    requires_confirmation: bool


class TimingEvent(BaseModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    event_type: TimingEventType
    client_time: datetime
    server_time: datetime
    timer_elapsed_seconds: int | None = Field(default=None, ge=0)
    timer_active_seconds: int | None = Field(default=None, ge=0)
    client_sequence: int | None = Field(default=None, ge=0)
    client_mutation_id: str
    client_device_id: str
    idempotency_key: str
    capture_context_snapshot_id: UUID | None = None
    capture_context_snapshot_ref: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TimingEventSpan(BaseModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    checkpoint_run_id: UUID | None = None
    span_type: TemporalSpanType
    friction_category: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    count_policy: CountPolicy
    count_in_wall_time: bool = True
    count_in_active_time: bool = False
    model_update_scopes: list[str] = Field(default_factory=list)
    linked_annotation_id: UUID | None = None
    linked_extracted_event_id: UUID | None = None
    user_corrected: bool = False


class TimingReviewFlag(BaseModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    snapshot_id: UUID | None = None
    flag_type: TimingReviewFlagType
    status: TimingReviewFlagStatus = TimingReviewFlagStatus.open
    severity: Severity = Severity.medium
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason_code: str
    user_message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    resolved_at: datetime | None = None
    resolution_note: str | None = None


class UpdateTimingReviewFlagRequest(BaseModel):
    mutation: MutationEnvelope
    status: TimingReviewFlagStatus
    resolution_note: str | None = None


class TimingSession(BaseModel):
    id: UUID
    user_id: UUID
    activity_id: UUID
    client_session_id: str | None = None
    source_device_id: str | None = None
    mode: TimingMode
    status: TimingSessionStatus
    work_mode: str = "unknown"
    actor_mode: str = "unknown"
    intended_start_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    active_seconds: int | None = Field(default=None, ge=0)
    wall_seconds: int | None = Field(default=None, ge=0)
    setup_seconds: int | None = Field(default=None, ge=0)
    detour_seconds: int | None = Field(default=None, ge=0)
    interruption_seconds: int | None = Field(default=None, ge=0)
    waiting_seconds: int | None = Field(default=None, ge=0)
    side_quest_seconds: int | None = Field(default=None, ge=0)
    start_latency_seconds: int | None = Field(default=None, ge=0)
    transition_seconds: int | None = Field(default=None, ge=0)
    run_quality: str = "unknown"
    model_inclusion: str = "not_reviewed"
    needs_timeline_recompute: bool = False
    events: list[TimingEvent] = Field(default_factory=list)
    spans: list[TimingEventSpan] = Field(default_factory=list)


class CreateTimingSessionRequest(BaseModel):
    mutation: MutationEnvelope
    activity_id: UUID
    client_session_id: str
    mode: TimingMode = TimingMode.whole_task
    work_mode: str = "unknown"
    actor_mode: str = "unknown"
    intended_start_at: datetime | None = None
    user_pre_estimate_seconds: int | None = Field(default=None, ge=0)


class AppendTimingEventRequest(BaseModel):
    mutation: MutationEnvelope
    event_type: TimingEventType
    client_time: datetime
    timer_elapsed_seconds: int | None = Field(default=None, ge=0)
    timer_active_seconds: int | None = Field(default=None, ge=0)
    capture_context_snapshot_id: UUID | None = None
    capture_context_snapshot_ref: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CaptureMethod(StrEnum):
    manual_timer_button = "manual_timer_button"
    lock_screen_widget = "lock_screen_widget"
    home_screen_widget = "home_screen_widget"
    watch = "watch"
    voice = "voice"
    quick_chip = "quick_chip"
    shortcut = "shortcut"
    nfc_tag = "nfc_tag"
    calendar_import = "calendar_import"
    system_detected = "system_detected"
    review_reconstruction = "review_reconstruction"
    background_signal = "background_signal"
    api = "api"


class CaptureTrigger(StrEnum):
    user_initiated = "user_initiated"
    timer_event = "timer_event"
    annotation = "annotation"
    checkpoint_event = "checkpoint_event"
    permission_change = "permission_change"
    geofence_transition = "geofence_transition"
    place_visit = "place_visit"
    radio_fingerprint_change = "radio_fingerprint_change"
    motion_change = "motion_change"
    sync_replay = "sync_replay"
    review = "review"


class SensorAvailabilityState(StrEnum):
    available = "available"
    permission_denied = "permission_denied"
    disabled_by_user = "disabled_by_user"
    disabled_by_system = "disabled_by_system"
    unsupported = "unsupported"
    unavailable = "unavailable"
    not_requested = "not_requested"
    stale = "stale"


class SensorRetentionPolicy(StrEnum):
    do_not_store = "do_not_store"
    derived_only = "derived_only"
    short_ttl_raw = "short_ttl_raw"
    store_with_consent = "store_with_consent"


class FeatureFamily(StrEnum):
    duration_prediction = "duration_prediction"
    start_latency = "start_latency"
    transition_latency = "transition_latency"
    friction = "friction"
    place_inference = "place_inference"
    prompt_policy = "prompt_policy"
    anomaly_detection = "anomaly_detection"


class PrivacyDeleteScope(StrEnum):
    raw_context = "raw_context"
    location_context = "location_context"
    radio_context = "radio_context"
    place_context = "place_context"
    context_features = "context_features"
    audio = "audio"
    activity = "activity"
    account = "account"


class GeospatialSourceType(StrEnum):
    fused_location = "fused_location"
    gps = "gps"
    network_location = "network_location"
    wifi_derived = "wifi_derived"
    wifi_rtt = "wifi_rtt"
    ble_beacon = "ble_beacon"
    ibeacon = "ibeacon"
    uwb = "uwb"
    cell = "cell"
    manual_place = "manual_place"
    geofence = "geofence"
    visit = "visit"
    significant_location_change = "significant_location_change"
    none = "none"


class RadioSourceType(StrEnum):
    wifi_connected_network = "wifi_connected_network"
    wifi_scan = "wifi_scan"
    wifi_rtt = "wifi_rtt"
    ble_scan = "ble_scan"
    ibeacon = "ibeacon"
    uwb = "uwb"
    cell = "cell"
    unknown = "unknown"


class MotionState(StrEnum):
    unknown = "unknown"
    stationary = "stationary"
    walking = "walking"
    running = "running"
    cycling = "cycling"
    driving = "driving"
    in_vehicle = "in_vehicle"
    transit = "transit"
    mixed = "mixed"


class PlaceCategory(StrEnum):
    unknown = "unknown"
    home = "home"
    work = "work"
    office = "office"
    kitchen = "kitchen"
    garage = "garage"
    yard = "yard"
    store = "store"
    gym = "gym"
    vehicle = "vehicle"
    public = "public"
    client_site = "client_site"
    medical = "medical"
    school = "school"
    religious = "religious"
    other = "other"


class UserPlace(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    category: PlaceCategory = PlaceCategory.unknown
    latitude: float | None = None
    longitude: float | None = None
    radius_meters: int | None = Field(default=None, ge=1)
    source: GeospatialSourceType = GeospatialSourceType.manual_place
    privacy_class: PrivacyClass = PrivacyClass.normal
    confirmed_by_user: bool = False
    is_sensitive: bool = False
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ResolvePlaceMatchType(StrEnum):
    existing_place = "existing_place"
    inferred_candidate = "inferred_candidate"
    manual_candidate = "manual_candidate"
    no_match = "no_match"


class ResolvedPlaceCandidate(BaseModel):
    place: UserPlace | None = None
    candidate_label: str | None = None
    candidate_category: PlaceCategory = PlaceCategory.unknown
    confidence: float = Field(ge=0, le=1)
    match_type: ResolvePlaceMatchType
    evidence: dict[str, Any] = Field(default_factory=dict)


class ResolvePlaceResponse(BaseModel):
    candidates: list[ResolvedPlaceCandidate]
    recommended_place_id: UUID | None = None
    requires_confirmation: bool


class GeospatialObservation(BaseModel):
    id: UUID | None = None
    user_id: UUID | None = None
    snapshot_id: UUID | None = None
    source: GeospatialSourceType
    observed_at: datetime
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    altitude_meters: float | None = None
    horizontal_accuracy_meters: float | None = Field(default=None, ge=0)
    vertical_accuracy_meters: float | None = Field(default=None, ge=0)
    speed_mps: float | None = None
    course_degrees: float | None = Field(default=None, ge=0, le=360)
    is_precise: bool = False
    is_stale: bool = False
    staleness_seconds: int | None = Field(default=None, ge=0)
    privacy_class: PrivacyClass = PrivacyClass.normal
    retention_policy: SensorRetentionPolicy = SensorRetentionPolicy.derived_only
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class RadioObservation(BaseModel):
    id: UUID | None = None
    user_id: UUID | None = None
    snapshot_id: UUID | None = None
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
    privacy_class: PrivacyClass = PrivacyClass.sensitive
    retention_policy: SensorRetentionPolicy = SensorRetentionPolicy.derived_only
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class DeviceContextObservation(BaseModel):
    id: UUID | None = None
    user_id: UUID | None = None
    snapshot_id: UUID | None = None
    observed_at: datetime
    motion_state: MotionState = MotionState.unknown
    battery_percent: int | None = Field(default=None, ge=0, le=100)
    charging_state: str = "unknown"
    network_state: str = "unknown"
    device_type: str = "unknown"
    app_foreground_state: str = "unknown"
    privacy_class: PrivacyClass = PrivacyClass.normal
    retention_policy: SensorRetentionPolicy = SensorRetentionPolicy.derived_only
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class InferredPlaceObservation(BaseModel):
    id: UUID | None = None
    user_id: UUID | None = None
    snapshot_id: UUID | None = None
    user_place_id: UUID | None = None
    candidate_label: str | None = None
    candidate_category: PlaceCategory = PlaceCategory.unknown
    confidence: float = Field(ge=0, le=1)
    confirmation_state: ConfirmationState = ConfirmationState.needs_confirmation
    evidence: dict[str, Any] = Field(default_factory=dict)
    sensitive_label_detected: bool = False
    confirmed_at: datetime | None = None
    created_at: datetime | None = None


class ContextCapturePolicy(BaseModel):
    id: UUID
    user_id: UUID
    location_enabled: bool = False
    precise_location_enabled: bool = False
    background_location_enabled: bool = False
    radio_context_enabled: bool = False
    motion_context_enabled: bool = False
    device_context_enabled: bool = True
    raw_location_retention_days: int | None = Field(default=None, ge=0)
    raw_radio_retention_days: int | None = Field(default=None, ge=0)
    default_location_retention_policy: SensorRetentionPolicy = SensorRetentionPolicy.derived_only
    default_radio_retention_policy: SensorRetentionPolicy = SensorRetentionPolicy.derived_only
    per_run_context_default: bool = True
    updated_at: datetime
    created_at: datetime


class UpdateContextCapturePolicyRequest(BaseModel):
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


class PrivacyDeleteRequest(BaseModel):
    mutation: MutationEnvelope
    delete_scope: PrivacyDeleteScope
    entity_id: UUID | None = None
    confirm: bool


class CaptureContextSnapshot(BaseModel):
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
    app_foreground_state: str = "unknown"
    location_state: SensorAvailabilityState = SensorAvailabilityState.not_requested
    radio_state: SensorAvailabilityState = SensorAvailabilityState.not_requested
    motion_state_available: SensorAvailabilityState = SensorAvailabilityState.not_requested
    device_context_state: SensorAvailabilityState = SensorAvailabilityState.available
    privacy_class: PrivacyClass = PrivacyClass.normal
    retention_policy: SensorRetentionPolicy = SensorRetentionPolicy.derived_only
    context_quality_score: float | None = Field(default=None, ge=0, le=1)
    permission_summary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    geospatial_observations: list[GeospatialObservation] = Field(default_factory=list)
    radio_observations: list[RadioObservation] = Field(default_factory=list)
    device_context_observations: list[DeviceContextObservation] = Field(default_factory=list)
    inferred_places: list[InferredPlaceObservation] = Field(default_factory=list)
    client_mutation_id: str
    client_device_id: str
    idempotency_key: str
    created_at: datetime


class CreateCaptureContextSnapshotRequest(BaseModel):
    mutation: MutationEnvelope
    checkpoint_run_id: UUID | None = None
    user_place_id: UUID | None = None
    capture_method: CaptureMethod
    capture_trigger: CaptureTrigger
    client_captured_at: datetime
    client_monotonic_millis: int | None = Field(default=None, ge=0)
    source_device_id: str
    app_foreground_state: str = "unknown"
    location_state: SensorAvailabilityState = SensorAvailabilityState.not_requested
    radio_state: SensorAvailabilityState = SensorAvailabilityState.not_requested
    motion_state_available: SensorAvailabilityState = SensorAvailabilityState.not_requested
    device_context_state: SensorAvailabilityState = SensorAvailabilityState.available
    privacy_class: PrivacyClass = PrivacyClass.normal
    retention_policy: SensorRetentionPolicy = SensorRetentionPolicy.derived_only
    context_quality_score: float | None = Field(default=None, ge=0, le=1)
    permission_summary: dict[str, Any] = Field(default_factory=dict)
    geospatial_observations: list[GeospatialObservation] = Field(default_factory=list)
    radio_observations: list[RadioObservation] = Field(default_factory=list)
    device_context_observations: list[DeviceContextObservation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemporalFeatureVector(BaseModel):
    id: UUID
    user_id: UUID
    activity_id: UUID | None = None
    session_id: UUID | None = None
    snapshot_id: UUID | None = None
    feature_schema_version: str = "1.3.0"
    feature_family: FeatureFamily
    features: dict[str, Any]
    source_entity_refs: list[dict[str, Any]] = Field(default_factory=list)
    privacy_class: PrivacyClass = PrivacyClass.normal
    model_eligible: bool = False
    exclusion_reason: str | None = None
    generated_at: datetime


class UpdatePlaceRequest(BaseModel):
    mutation: MutationEnvelope
    display_name: str | None = None
    category: PlaceCategory | None = None
    radius_meters: int | None = Field(default=None, ge=1)
    privacy_class: PrivacyClass | None = None
    confirmed_by_user: bool | None = None
    is_sensitive: bool | None = None
    aliases: list[str] | None = None


class CreatePlaceRequest(BaseModel):
    mutation: MutationEnvelope
    display_name: str
    category: PlaceCategory = PlaceCategory.unknown
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_meters: int | None = Field(default=None, ge=1)
    source: GeospatialSourceType = GeospatialSourceType.manual_place
    privacy_class: PrivacyClass = PrivacyClass.normal
    confirmed_by_user: bool = True
    is_sensitive: bool = False
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecomputeFeatureVectorsRequest(BaseModel):
    mutation: MutationEnvelope
    user_id: UUID | None = None
    activity_id: UUID | None = None
    session_id: UUID | None = None
    feature_families: list[FeatureFamily]
    reason: str


class SyncPushRequest(BaseModel):
    mutation: MutationEnvelope
    client_device_id: str
    mutations: list[dict[str, Any]]
