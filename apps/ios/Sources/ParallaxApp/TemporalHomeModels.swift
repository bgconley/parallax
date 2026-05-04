import Foundation
import ParallaxCore

public enum TemporalHomeSurfaceState: String, CaseIterable, Sendable {
    case defaultHome = "default"
    case needsReview = "needs_review"
    case syncPending = "sync_pending"
    case expandedTimingRun = "expanded_timing_run"
    case groundedAnswer = "grounded_answer"
}

public enum TemporalHomeActionClassification: String, CaseIterable, Sendable {
    case drawer
    case navigation
    case localQueue = "local_queue"
    case apiWorkflow = "api_workflow"
    case displayOnly = "display_only"
}

public enum TemporalHomeDrawerKind: Equatable, Sendable {
    case temporalNavigation
    case quickCapture
    case syncQueue
    case timingRunEvidence
    case temporalAnswerEvidence
    case phase8(Phase8DrawerWorkflow)
}

public enum TemporalHomeRoute: Equatable, Sendable {
    case drawer(TemporalHomeDrawerKind)
    case surface(TemporalHomeSurfaceState)
    case timingLauncher
    case displayOnly
}

public enum TemporalHomeAction: String, CaseIterable, Sendable {
    case menuDefault = "118_9_menu"
    case temporalActionDefault = "118_9_temporal_action"
    case currentFocusDefault = "118_9_current_focus"
    case preflightInsightDefault = "118_9_preflight_insight"
    case runningRowDefault = "118_9_running_row"
    case preflightRowDefault = "118_9_preflight_row"
    case waitingRowDefault = "118_9_waiting_row"
    case baselineRowDefault = "118_9_baseline_row"
    case groundedRowDefault = "118_9_grounded_row"
    case evidenceCurrentRowDefault = "118_9_evidence_current_row"
    case quickCaptureDefault = "118_9_quick_capture"
    case reviewRunDefault = "118_9_review_run"
    case askTimeDefault = "118_9_ask_time"
    case menuNeedsReview = "118_104_menu"
    case temporalActionNeedsReview = "118_104_temporal_action"
    case reviewFocusNeedsReview = "118_104_review_focus"
    case learningImpactNeedsReview = "118_104_learning_impact"
    case kitchenReviewRowNeedsReview = "118_104_kitchen_review_row"
    case eveningCorrectRowNeedsReview = "118_104_evening_correct_row"
    case packLunchRowNeedsReview = "118_104_pack_lunch_row"
    case spongeCheckRowNeedsReview = "118_104_sponge_check_row"
    case pansSampleRowNeedsReview = "118_104_pans_sample_row"
    case queueReadyRowNeedsReview = "118_104_queue_ready_row"
    case quickCaptureNeedsReview = "118_104_quick_capture"
    case reviewAllNeedsReview = "118_104_review_all"
    case askImpactNeedsReview = "118_104_ask_impact"
    case menuSyncPending = "118_199_menu"
    case temporalActionSyncPending = "118_199_temporal_action"
    case syncFocusSyncPending = "118_199_sync_focus"
    case syncBehaviorSyncPending = "118_199_sync_behavior"
    case sessionStartedRowSyncPending = "118_199_session_started_row"
    case resourceDetourRowSyncPending = "118_199_resource_detour_row"
    case reviewSavedRowSyncPending = "118_199_review_saved_row"
    case preflightDecisionRowSyncPending = "118_199_preflight_decision_row"
    case bearerRetryRowSyncPending = "118_199_bearer_retry_row"
    case sequenceSafeRowSyncPending = "118_199_sequence_safe_row"
    case quickCaptureSyncPending = "118_199_quick_capture"
    case retrySyncPending = "118_199_retry_sync"
    case viewQueueSyncPending = "118_199_view_queue"
    case openReviewExpandedRun = "118_294_open_review"
    case askSimilarTimeExpandedRun = "118_294_ask_similar_time"
    case startAgainExpandedRun = "118_294_start_again"
    case menuGroundedAnswer = "118_346_menu"
    case temporalActionGroundedAnswer = "118_346_temporal_action"
    case questionFocusGroundedAnswer = "118_346_question_focus"
    case answerSummaryGroundedAnswer = "118_346_answer_summary"
    case reviewedRunsRowGroundedAnswer = "118_346_reviewed_runs_row"
    case resourceDetoursRowGroundedAnswer = "118_346_resource_detours_row"
    case rawNotesRowGroundedAnswer = "118_346_raw_notes_row"
    case medianRowGroundedAnswer = "118_346_median_row"
    case slowCaseRowGroundedAnswer = "118_346_slow_case_row"
    case beforeStartingRowGroundedAnswer = "118_346_before_starting_row"
    case askAnotherGroundedAnswer = "118_346_ask_another"
    case startTimerGroundedAnswer = "118_346_start_timer"
    case useCheckGroundedAnswer = "118_346_use_check"
}

public struct TemporalHomeActionSpec: Equatable, Sendable {
    public let action: TemporalHomeAction
    public let label: String
    public let screenNode: String
    public let classification: TemporalHomeActionClassification
    public let route: TemporalHomeRoute
    public let workflow: String

    public init(
        action: TemporalHomeAction,
        label: String,
        screenNode: String,
        classification: TemporalHomeActionClassification,
        route: TemporalHomeRoute,
        workflow: String
    ) {
        self.action = action
        self.label = label
        self.screenNode = screenNode
        self.classification = classification
        self.route = route
        self.workflow = workflow
    }
}
