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
            await timingViewModel.confirmSpongeEvidence()
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
            await timingViewModel.decidePreflightCheck(.accept)
        case .snoozePreflight:
            await timingViewModel.decidePreflightCheck(.snooze)
        case .hidePreflight:
            await timingViewModel.decidePreflightCheck(.hide)
        case .retirePreflight:
            await timingViewModel.decidePreflightCheck(.retire)
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

    public func saveQuickCapture() async {
        await timingViewModel.captureTemporalHomeNote("Captured timing evidence from Temporal Home.")
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
            await timingViewModel.captureTemporalHomeNote("Captured timing evidence from Temporal Home.")
        default:
            break
        }
    }

    private func askTemporalQuestion(_ question: String) async {
        lastTemporalQuestion = question
        await timingViewModel.recordTemporalQueryIntent(question)
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
            return "What is the usual baseline for pack lunch?"
        case .learningImpactNeedsReview, .askImpactNeedsReview:
            return "What changes if I approve these timing runs?"
        case .pansSampleRowNeedsReview:
            return "How many samples support hand-wash pans?"
        case .askSimilarTimeExpandedRun:
            return "How long do similar kitchen cleanup runs take?"
        case .askAnotherGroundedAnswer:
            return "Ask another grounded time question."
        default:
            return "How long does clean pots and pans usually take?"
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
}
