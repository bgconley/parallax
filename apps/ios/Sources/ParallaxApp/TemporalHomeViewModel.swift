import Foundation
import ParallaxCore

@MainActor
public final class TemporalHomeViewModel: ObservableObject {
    @Published public private(set) var surfaceState: TemporalHomeSurfaceState
    @Published public var activeDrawer: TemporalHomeDrawerKind?
    @Published public private(set) var showsLauncher = false
    @Published public private(set) var lastAction: TemporalHomeAction?
    @Published public private(set) var lastTemporalQuestion: String?

    public let timingViewModel: TimingSliceViewModel

    public init(
        timingViewModel: TimingSliceViewModel,
        initialSurface: TemporalHomeSurfaceState? = nil
    ) {
        self.timingViewModel = timingViewModel
        self.surfaceState = initialSurface ?? Self.surface(for: timingViewModel.projection)
    }

    public func dismissDrawer() {
        activeDrawer = nil
    }

    public func dismissLauncher() {
        showsLauncher = false
    }

    public func setSurface(_ surface: TemporalHomeSurfaceState) {
        surfaceState = surface
    }

    public func perform(_ action: TemporalHomeAction) async {
        lastAction = action
        if routeDraftTimingFocusToLauncher(action) {
            showsLauncher = true
            return
        }
        if suppressReviewWithoutCompletedRun(action) {
            return
        }
        let spec = TemporalHomeActionMap.spec(for: action)
        switch spec.classification {
        case .apiWorkflow:
            await askTemporalQuestion(question(for: action))
        case .localQueue:
            await performLocalQueueAction(action)
        case .drawer, .navigation, .displayOnly:
            break
        }
        apply(spec.route)
    }

    public func performDrawerAction(_ action: Phase8DrawerAction) async {
        switch action {
        case .completeStep:
            await timingViewModel.completeCurrentCheckpoint()
        case .pauseStep:
            await timingViewModel.pauseCurrentStep()
        case .skipStep:
            await timingViewModel.skipCurrentCheckpoint()
        case .moveStep:
            await timingViewModel.moveCurrentCheckpoint()
        case .addStepNote:
            await timingViewModel.captureStepNote()
        case .confirmFrictionEvidence:
            await timingViewModel.confirmFrictionEvidence(
                resourceName: "missing resource",
                note: timingViewModel.detourNote ?? "Confirmed friction evidence.",
                suggestedPreflightText: nil
            )
        case .correctFrictionEvidence:
            await timingViewModel.correctFrictionEvidence()
        case .ignoreFrictionEvidence:
            await timingViewModel.ignoreFrictionEvidence()
        case .keepFrictionNoteOnly:
            await timingViewModel.keepFrictionNoteOnly()
        case .trimForgottenTimer:
            await timingViewModel.trimForgottenTimerAtPlaceChange()
        case .timerKeptRunning:
            await timingViewModel.timerKeptRunningAfterPlaceChange()
        case .forgottenTimerNotSure:
            await timingViewModel.deferForgottenTimerDecision()
        case .saveUsefulRun:
            await timingViewModel.saveReviewDecision(.saveUsefulRun)
        case .markUnusual:
            await timingViewModel.saveReviewDecision(.markUnusual)
        case .activeTimeOnly:
            await timingViewModel.saveReviewDecision(.activeOnly)
        case .frictionEvidenceOnly:
            await timingViewModel.saveReviewDecision(.frictionOnly)
        case .discardTimingKeepNote:
            await timingViewModel.discardTimingKeepNote()
        case .keepPreflightActive:
            await timingViewModel.decidePreflightCheck(.accept, checkId: nil)
        case .snoozePreflight:
            await timingViewModel.decidePreflightCheck(.snooze, checkId: nil)
        case .hidePreflight:
            await timingViewModel.decidePreflightCheck(.hide, checkId: nil)
        case .retirePreflight:
            await timingViewModel.decidePreflightCheck(.retire, checkId: nil)
        case .viewPreflightRuns:
            surfaceState = .expandedTimingRun
        case .updateCheckpointPlan:
            await timingViewModel.updateCheckpointPlan()
        case .makeCheckpointOptional:
            await timingViewModel.makeCheckpointOptional()
        case .startFromCheckpoint:
            await timingViewModel.startFromCurrentCheckpoint()
        }
        activeDrawer = nil
    }

    public func saveQuickCapture(_ note: String) async {
        await timingViewModel.captureTemporalHomeNote(note)
        activeDrawer = nil
    }

    public func retrySync() async {
        await timingViewModel.retrySyncNow()
    }

    private func performLocalQueueAction(_ action: TemporalHomeAction) async {
        switch action {
        case .bearerRetryRowSyncPending, .retrySyncPending:
            await retrySync()
        case .quickCaptureDefault, .quickCaptureNeedsReview, .quickCaptureSyncPending:
            await timingViewModel.captureTemporalHomeNote("Captured timing evidence from the home screen.")
        default:
            break
        }
    }

    private func askTemporalQuestion(_ question: String) async {
        lastTemporalQuestion = question
        await timingViewModel.submitTemporalQuery(question)
    }

    private func apply(_ route: TemporalHomeRoute) {
        switch route {
        case let .drawer(drawer):
            activeDrawer = drawer
        case let .surface(surface):
            surfaceState = surface
        case .timingLauncher:
            showsLauncher = true
        case .displayOnly:
            break
        }
    }

    private func question(for action: TemporalHomeAction) -> String {
        switch action {
        case .baselineRowDefault:
            return "What is the usual baseline for \(timingViewModel.activityName)?"
        case .learningImpactNeedsReview, .askImpactNeedsReview:
            return "What changes if I approve these timing runs?"
        case .sampleSupportRowNeedsReview:
            return "How many samples support \(timingViewModel.activityName)?"
        case .askSimilarTimeExpandedRun:
            return "How long do similar \(timingViewModel.activityName) runs take?"
        case .askAnotherGroundedAnswer:
            return "Ask another grounded time question."
        default:
            return "How long does \(timingViewModel.activityName) usually take?"
        }
    }

    private static func surface(for projection: TimingSessionProjection) -> TemporalHomeSurfaceState {
        if projection.needsReview || projection.primaryState == .needsReview {
            return .needsReview
        }
        if projection.hasPendingSync || projection.primaryState == .syncPending {
            return .syncPending
        }
        return .defaultHome
    }

    private func routeDraftTimingFocusToLauncher(_ action: TemporalHomeAction) -> Bool {
        guard action == .currentFocusDefault || action == .runningRowDefault else {
            return false
        }
        return timingViewModel.canStart
    }

    private func suppressReviewWithoutCompletedRun(_ action: TemporalHomeAction) -> Bool {
        switch action {
        case .reviewRunDefault, .reviewFocusNeedsReview, .runReviewRowNeedsReview,
             .baselineSampleRowNeedsReview, .reviewAllNeedsReview, .openReviewExpandedRun:
            return !(timingViewModel.canSaveReview || timingViewModel.status == .reviewed)
        default:
            return false
        }
    }
}
