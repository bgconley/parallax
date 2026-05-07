import Foundation
import ParallaxCore

public enum Phase8DrawerWorkflow: String, CaseIterable, Identifiable, Sendable {
    case stepDetail = "step_detail"
    case frictionEvidence = "friction_evidence"
    case forgottenTimer = "forgotten_timer"
    case reviewDecision = "review_decision"
    case preflightEvidence = "preflight_evidence"
    case checkpointSetup = "checkpoint_setup"

    public var id: String { rawValue }

    public init?(rawDemoValue: String) {
        switch rawDemoValue {
        case "step_detail", "steps":
            self = .stepDetail
        case "friction_evidence", "friction":
            self = .frictionEvidence
        case "forgotten_timer", "time_review":
            self = .forgottenTimer
        case "review_decision", "privacy":
            self = .reviewDecision
        case "preflight_evidence", "preflight":
            self = .preflightEvidence
        case "checkpoint_setup":
            self = .checkpointSetup
        default:
            return nil
        }
    }
}

public enum Phase8DrawerAction: String, CaseIterable, Equatable, Sendable {
    case completeStep = "complete_step"
    case pauseStep = "pause_step"
    case skipStep = "skip_step"
    case moveStep = "move_step"
    case addStepNote = "add_step_note"
    case confirmFrictionEvidence = "confirm_friction_evidence"
    case correctFrictionEvidence = "correct_friction_evidence"
    case ignoreFrictionEvidence = "ignore_friction_evidence"
    case keepFrictionNoteOnly = "keep_friction_note_only"
    case trimForgottenTimer = "trim_forgotten_timer"
    case timerKeptRunning = "timer_kept_running"
    case forgottenTimerNotSure = "forgotten_timer_not_sure"
    case saveUsefulRun = "save_useful_run"
    case markUnusual = "mark_unusual"
    case savePartial = "save_partial"
    case activeTimeOnly = "active_time_only"
    case frictionEvidenceOnly = "friction_evidence_only"
    case queryEvidenceOnly = "query_evidence_only"
    case discardTimingKeepNote = "discard_timing_keep_note"
    case discardAll = "discard_all"
    case keepPreflightActive = "keep_preflight_active"
    case snoozePreflight = "snooze_preflight"
    case hidePreflight = "hide_preflight"
    case retirePreflight = "retire_preflight"
    case viewPreflightRuns = "view_preflight_runs"
    case updateCheckpointPlan = "update_checkpoint_plan"
    case makeCheckpointOptional = "make_checkpoint_optional"
    case startFromCheckpoint = "start_from_checkpoint"
}

public struct ReviewDecisionDisplay: Equatable, Sendable {
    public let decision: ModelUpdateDecision
    public let modelInclusion: ModelInclusion
    public let scopes: [ReviewLearningScope]
    public let title: String
    public let subtitle: String
    public let selected: Bool

    public init(
        decision: ModelUpdateDecision,
        modelInclusion: ModelInclusion,
        scopes: [ReviewLearningScope],
        title: String,
        subtitle: String,
        selected: Bool
    ) {
        self.decision = decision
        self.modelInclusion = modelInclusion
        self.scopes = scopes
        self.title = title
        self.subtitle = subtitle
        self.selected = selected
    }
}

public enum ReviewDecisionDisplayFactory {
    public static func options(selected decision: ModelUpdateDecision = .saveUsefulRun) -> [ReviewDecisionDisplay] {
        [
            ReviewDecisionDisplay(
                decision: .saveUsefulRun,
                modelInclusion: .full,
                scopes: [.activeDuration, .wallDuration, .frictionPatterns, .preflightSuggestions],
                title: "Useful normal run",
                subtitle: "active + wall + friction + checkpoints",
                selected: decision == .saveUsefulRun
            ),
            ReviewDecisionDisplay(
                decision: .markUnusual,
                modelInclusion: .full,
                scopes: [.activeDuration, .wallDuration, .frictionPatterns],
                title: "Unusual but useful",
                subtitle: "keep evidence with an unusual marker",
                selected: decision == .markUnusual
            ),
            ReviewDecisionDisplay(
                decision: .savePartial,
                modelInclusion: .activeDurationOnly,
                scopes: [.activeDuration],
                title: "Useful partial run",
                subtitle: "learn partial active time only",
                selected: decision == .savePartial
            ),
            ReviewDecisionDisplay(
                decision: .activeOnly,
                modelInclusion: .activeDurationOnly,
                scopes: [.activeDuration],
                title: "Active time only",
                subtitle: "do not update wall-time baseline",
                selected: decision == .activeOnly
            ),
            ReviewDecisionDisplay(
                decision: .frictionOnly,
                modelInclusion: .frictionPatternsOnly,
                scopes: [.frictionPatterns, .preflightSuggestions],
                title: "Friction / evidence only",
                subtitle: "learn blockers, not duration baseline",
                selected: decision == .frictionOnly
            ),
            ReviewDecisionDisplay(
                decision: .queryEvidenceOnly,
                modelInclusion: .queryEvidenceOnly,
                scopes: [],
                title: "Evidence for answers only",
                subtitle: "ground Ask without updating predictions",
                selected: decision == .queryEvidenceOnly
            ),
            ReviewDecisionDisplay(
                decision: .discardTimingKeepNote,
                modelInclusion: .exclude,
                scopes: [],
                title: "Discard timing, keep note",
                subtitle: "source note stays; run does not teach timing",
                selected: decision == .discardTimingKeepNote
            ),
            ReviewDecisionDisplay(
                decision: .discardAll,
                modelInclusion: .exclude,
                scopes: [],
                title: "Discard all",
                subtitle: "exclude timing and context from learning",
                selected: decision == .discardAll
            ),
        ]
    }

    public static func option(for decision: ModelUpdateDecision) -> ReviewDecisionDisplay {
        options(selected: decision).first { $0.decision == decision }
            ?? options(selected: .saveUsefulRun)[0]
    }
}
