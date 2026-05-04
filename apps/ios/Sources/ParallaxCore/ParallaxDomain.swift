import Foundation
import ParallaxDesignSystem

public enum TimingSessionStatus: String, Codable, CaseIterable, Sendable {
    case draft
    case intentRecorded = "intent_recorded"
    case running
    case paused
    case completedUnreviewed = "completed_unreviewed"
    case reviewed
    case discarded
    case abandoned
}

public enum TimingEventType: String, Codable, CaseIterable, Sendable {
    case intentRecorded = "intent_recorded"
    case sessionStarted = "session_started"
    case sessionPaused = "session_paused"
    case sessionResumed = "session_resumed"
    case sessionCompleted = "session_completed"
    case sessionAbandoned = "session_abandoned"
    case checkpointStarted = "checkpoint_started"
    case checkpointCompleted = "checkpoint_completed"
    case checkpointSkipped = "checkpoint_skipped"
    case annotationCaptured = "annotation_captured"
    case extractedEventCreated = "extracted_event_created"
    case activeWorkStarted = "active_work_started"
    case activeWorkCompleted = "active_work_completed"
    case setupStarted = "setup_started"
    case setupCompleted = "setup_completed"
    case resourceDetourStarted = "resource_detour_started"
    case resourceDetourCompleted = "resource_detour_completed"
    case interruptionStarted = "interruption_started"
    case interruptionCompleted = "interruption_completed"
    case waitingStarted = "waiting_started"
    case waitingCompleted = "waiting_completed"
    case sideQuestStarted = "side_quest_started"
    case sideQuestCompleted = "side_quest_completed"
    case transitionStarted = "transition_started"
    case transitionCompleted = "transition_completed"
    case badTimerMarked = "bad_timer_marked"
    case scopeChanged = "scope_changed"
    case userCorrectionApplied = "user_correction_applied"
    case reviewSaved = "review_saved"
    case syncReconciled = "sync_reconciled"
}

public enum TemporalSpanType: String, Codable, CaseIterable, Sendable {
    case activeWork = "active_work"
    case setup
    case resourceDetour = "resource_detour"
    case interruption
    case waiting
    case sideQuest = "side_quest"
    case startLatency = "start_latency"
    case transition
    case bodyEnergy = "body_energy"
    case decisionLoop = "decision_loop"
    case attentionDrift = "attention_drift"
    case environmentFriction = "environment_friction"
    case badTimer = "bad_timer"
    case scopeChange = "scope_change"
    case other
}

public enum CountPolicy: String, Codable, CaseIterable, Sendable {
    case wallAndActive = "wall_and_active"
    case wallOnly = "wall_only"
    case activeOnly = "active_only"
    case separateStartLatency = "separate_start_latency"
    case separateTransition = "separate_transition"
    case doNotCount = "do_not_count"
    case reviewRequired = "review_required"
}

public enum ModelUpdateDecision: String, Codable, CaseIterable, Sendable {
    case saveUsefulRun = "save_useful_run"
    case markUnusual = "mark_unusual"
    case savePartial = "save_partial"
    case activeOnly = "active_only"
    case frictionOnly = "friction_only"
    case queryEvidenceOnly = "query_evidence_only"
    case discardTimingKeepNote = "discard_timing_keep_note"
    case discardAll = "discard_all"

    public var isDiscardDecision: Bool {
        self == .discardTimingKeepNote || self == .discardAll
    }
}

public enum ModelInclusion: String, Codable, CaseIterable, Sendable {
    case notReviewed = "not_reviewed"
    case full
    case activeDurationOnly = "active_duration_only"
    case wallEnvelopeOnly = "wall_envelope_only"
    case frictionPatternsOnly = "friction_patterns_only"
    case queryEvidenceOnly = "query_evidence_only"
    case exclude
}

public enum ReviewLearningScope: String, Codable, CaseIterable, Sendable {
    case activeDuration = "active_duration"
    case wallDuration = "wall_duration"
    case frictionPatterns = "friction_patterns"
    case preflightSuggestions = "preflight_suggestions"
    case startLatency = "start_latency"
    case transitionLatency = "transition_latency"
}

public enum MeasurementMode: String, Codable, CaseIterable, Sendable {
    case estimateOnly = "estimate_only"
    case wholeTask = "whole_task"
    case checkpointed
    case routine
    case calibration
    case passive
}

public enum AnnotationInputMode: String, Codable, CaseIterable, Sendable {
    case text
    case voice
    case quickChip = "quick_chip"
    case systemDetected = "system_detected"
    case reviewNote = "review_note"
}

public enum CaptureMethod: String, Codable, CaseIterable, Sendable {
    case manualButton = "manual_timer_button"
    case lockScreenWidget = "lock_screen_widget"
    case watch
    case voice
    case quickChip = "quick_chip"
    case shortcut
    case nfcTag = "nfc_tag"
    case calendarImport = "calendar_import"
    case reviewReconstruction = "review_reconstruction"
    case backgroundSignal = "background_signal"
}

public enum PreflightCheckDecision: String, Codable, CaseIterable, Sendable {
    case accept
    case hide
    case snooze
    case retire
}

public enum UIProjectionState: String, Codable, CaseIterable, Sendable {
    case defaultReady = "default"
    case empty
    case offlineCached = "offline_cached"
    case syncPending = "sync_pending"
    case aiPending = "ai_pending"
    case needsReview = "needs_review"
    case highContrast = "high_contrast"
    case dynamicTypeStress = "dynamic_type_stress"
    case running
    case paused
    case waitingActive = "waiting_active"
    case detourActive = "detour_active"
    case interruptionActive = "interruption_active"
    case sideQuestActive = "side_quest_active"
    case abandonedResumed = "abandoned_resumed"
    case forgotToStopCorrection = "forgot_to_stop_correction"
    case unresolvedInterpretation = "unresolved_interpretation"
}

public enum TemporalSemanticRole: String, Codable, CaseIterable, Sendable {
    case active
    case wall
    case checkpoint
    case detour
    case interruption
    case waiting
    case startLatency = "start_latency"
    case privacy
}

public struct SemanticChip: Equatable, Sendable {
    public let role: TemporalSemanticRole
    public let label: String
    public let systemImage: String

    public init(role: TemporalSemanticRole, label: String, systemImage: String) {
        self.role = role
        self.label = label
        self.systemImage = systemImage
    }
}

public struct TimingSessionProjection: Equatable, Sendable {
    public let status: TimingSessionStatus
    public let openSpan: TemporalSpanType?
    public let isOffline: Bool
    public let hasPendingSync: Bool
    public let hasUnresolvedInterpretation: Bool
    public let needsReview: Bool

    public init(
        status: TimingSessionStatus,
        openSpan: TemporalSpanType? = nil,
        isOffline: Bool = false,
        hasPendingSync: Bool = false,
        hasUnresolvedInterpretation: Bool = false,
        needsReview: Bool = false
    ) {
        self.status = status
        self.openSpan = openSpan
        self.isOffline = isOffline
        self.hasPendingSync = hasPendingSync
        self.hasUnresolvedInterpretation = hasUnresolvedInterpretation
        self.needsReview = needsReview
    }

    public var primaryState: UIProjectionState {
        if isOffline { return .offlineCached }
        if hasPendingSync { return .syncPending }
        if hasUnresolvedInterpretation { return .unresolvedInterpretation }
        if needsReview || status == .completedUnreviewed { return .needsReview }
        switch openSpan {
        case .waiting:
            return .waitingActive
        case .resourceDetour, .setup:
            return .detourActive
        case .interruption:
            return .interruptionActive
        case .sideQuest:
            return .sideQuestActive
        case .badTimer:
            return .forgotToStopCorrection
        default:
            break
        }
        switch status {
        case .running:
            return .running
        case .paused:
            return .paused
        case .abandoned:
            return .abandonedResumed
        default:
            return .defaultReady
        }
    }
}

public enum TemporalRoleMapper {
    public static func role(for spanType: TemporalSpanType) -> TemporalSemanticRole {
        switch spanType {
        case .activeWork:
            return .active
        case .waiting:
            return .waiting
        case .resourceDetour, .setup:
            return .detour
        case .interruption:
            return .interruption
        case .startLatency:
            return .startLatency
        case .transition, .sideQuest, .bodyEnergy, .decisionLoop, .attentionDrift,
             .environmentFriction, .badTimer, .scopeChange, .other:
            return .wall
        }
    }

    public static func chip(for spanType: TemporalSpanType) -> SemanticChip {
        switch role(for: spanType) {
        case .active:
            return SemanticChip(role: .active, label: "Active work", systemImage: "timer")
        case .wall:
            return SemanticChip(role: .wall, label: "Wall time", systemImage: "clock")
        case .checkpoint:
            return SemanticChip(role: .checkpoint, label: "Checkpoint", systemImage: "checklist")
        case .detour:
            return SemanticChip(role: .detour, label: "Detour", systemImage: "arrow.triangle.branch")
        case .interruption:
            return SemanticChip(role: .interruption, label: "Interrupted", systemImage: "exclamationmark.bubble")
        case .waiting:
            return SemanticChip(role: .waiting, label: "Waiting", systemImage: "hourglass")
        case .startLatency:
            return SemanticChip(role: .startLatency, label: "Getting started", systemImage: "figure.walk")
        case .privacy:
            return SemanticChip(role: .privacy, label: "Private", systemImage: "lock")
        }
    }
}

public enum DesignTokenMapper {
    public static func colorToken(for role: TemporalSemanticRole, soft: Bool = false) -> ParallaxDesignTokens.ColorToken {
        switch (role, soft) {
        case (.active, false): return .active
        case (.active, true): return .activeSoft
        case (.wall, false): return .wallText
        case (.wall, true): return .wall
        case (.checkpoint, false): return .checkpointText
        case (.checkpoint, true): return .checkpointSoft
        case (.detour, false): return .detourText
        case (.detour, true): return .detourSoft
        case (.interruption, false), (.startLatency, false): return .interruptionText
        case (.interruption, true), (.startLatency, true): return .interruptionSoft
        case (.waiting, false), (.privacy, false): return .waitingText
        case (.waiting, true), (.privacy, true): return .waitingSoft
        }
    }
}
