import Foundation
import ParallaxCore

public enum TemporalHomeActionMap {
    public static let all: [TemporalHomeActionSpec] = TemporalHomeAction.allCases.map { spec(for: $0) }

    public static func spec(for action: TemporalHomeAction) -> TemporalHomeActionSpec {
        switch action {
        case .menuDefault, .menuNeedsReview, .menuSyncPending, .menuGroundedAnswer:
            return action.spec(label: "Menu", classification: .drawer, route: .drawer(.temporalNavigation), workflow: "open_temporal_navigation")
        case .temporalActionDefault, .temporalActionNeedsReview, .temporalActionSyncPending, .temporalActionGroundedAnswer:
            return action.spec(label: "Temporal action", classification: .drawer, route: .drawer(.quickCapture), workflow: "open_quick_capture")
        case .currentFocusDefault, .runningRowDefault:
            return action.spec(label: "Current timing run", classification: .navigation, route: .surface(.expandedTimingRun), workflow: "open_timing_run_evidence")
        case .preflightInsightDefault, .preflightRowDefault, .preflightCheckRowNeedsReview, .beforeStartingRowGroundedAnswer, .useCheckGroundedAnswer:
            return action.spec(label: "Preflight evidence", classification: .drawer, route: .drawer(.phase8(.preflightEvidence)), workflow: "preflight_evidence")
        case .waitingRowDefault:
            return action.spec(label: "Waiting detail", classification: .drawer, route: .drawer(.phase8(.stepDetail)), workflow: "step_detail")
        case .baselineRowDefault, .learningImpactNeedsReview, .sampleSupportRowNeedsReview, .askTimeDefault, .askImpactNeedsReview, .askSimilarTimeExpandedRun, .askAnotherGroundedAnswer:
            return action.spec(label: "Ask About Time", classification: .drawer, route: .drawer(.askTime), workflow: "answer_temporal_query")
        case .groundedRowDefault:
            return action.spec(label: "Grounded temporal answer", classification: .navigation, route: .surface(.groundedAnswer), workflow: "open_grounded_answer")
        case .evidenceCurrentRowDefault, .questionFocusGroundedAnswer, .answerSummaryGroundedAnswer, .reviewedRunsRowGroundedAnswer, .rawNotesRowGroundedAnswer, .medianRowGroundedAnswer, .slowCaseRowGroundedAnswer:
            return action.spec(label: "Temporal answer evidence", classification: .drawer, route: .drawer(.temporalAnswerEvidence), workflow: "open_temporal_answer_evidence")
        case .quickCaptureDefault, .quickCaptureNeedsReview, .quickCaptureSyncPending:
            return action.spec(label: "Quick capture", classification: .localQueue, route: .drawer(.quickCapture), workflow: "annotation_captured")
        case .reviewRunDefault, .reviewFocusNeedsReview, .runReviewRowNeedsReview, .baselineSampleRowNeedsReview, .reviewAllNeedsReview, .openReviewExpandedRun:
            return action.spec(label: "Review decision", classification: .drawer, route: .drawer(.phase8(.reviewDecision)), workflow: "review_decision")
        case .eveningCorrectRowNeedsReview:
            return action.spec(label: "Forgotten timer", classification: .drawer, route: .drawer(.phase8(.forgottenTimer)), workflow: "forgotten_timer")
        case .queueReadyRowNeedsReview, .syncFocusSyncPending, .syncBehaviorSyncPending, .sessionStartedRowSyncPending, .resourceDetourRowSyncPending, .reviewSavedRowSyncPending, .preflightDecisionRowSyncPending, .viewQueueSyncPending:
            return action.spec(label: "Sync queue", classification: .drawer, route: .drawer(.syncQueue), workflow: "open_sync_queue")
        case .bearerRetryRowSyncPending, .retrySyncPending:
            return action.spec(label: "Retry sync", classification: .localQueue, route: .drawer(.syncQueue), workflow: "retry_sync")
        case .sequenceSafeRowSyncPending:
            return action.spec(label: "Sync order protected", classification: .displayOnly, route: .displayOnly, workflow: "display_only")
        case .startTimerDefault, .startAgainExpandedRun, .startTimerGroundedAnswer:
            return action.spec(label: "Start timer", classification: .navigation, route: .timingLauncher, workflow: "open_timing_launcher")
        case .resourceDetoursRowGroundedAnswer:
            return action.spec(label: "Resource detours", classification: .drawer, route: .drawer(.phase8(.frictionEvidence)), workflow: "friction_evidence")
        }
    }

    public static func spec(for rawValue: String) -> TemporalHomeActionSpec? {
        TemporalHomeAction(rawValue: rawValue).map(spec)
    }
}

private extension TemporalHomeAction {
    func spec(
        label: String,
        classification: TemporalHomeActionClassification,
        route: TemporalHomeRoute,
        workflow: String
    ) -> TemporalHomeActionSpec {
        TemporalHomeActionSpec(
            action: self,
            label: label,
            screenNode: screenNode,
            classification: classification,
            route: route,
            workflow: workflow
        )
    }

    var screenNode: String {
        let parts = rawValue.split(separator: "_")
        guard parts.count >= 2 else { return "" }
        return "\(parts[0]):\(parts[1])"
    }
}
