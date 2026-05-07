import Foundation
import ParallaxCore

@MainActor
public final class TemporalHomeViewModel: ObservableObject {
    @Published public private(set) var surfaceState: TemporalHomeSurfaceState
    @Published public var activeDrawer: TemporalHomeDrawerKind?
    @Published public private(set) var showsLauncher = false
    @Published public private(set) var lastAction: TemporalHomeAction?
    @Published public private(set) var lastTemporalQuestion: String?

    @Published public private(set) var timingViewModel: TimingSliceViewModel

    public init(
        timingViewModel: TimingSliceViewModel,
        initialSurface: TemporalHomeSurfaceState? = nil
    ) {
        self.timingViewModel = timingViewModel
        self.surfaceState = initialSurface ?? Self.surface(for: timingViewModel.projection)
    }

    public func attachTimingViewModel(_ viewModel: TimingSliceViewModel) {
        guard viewModel !== timingViewModel else { return }
        let previousActivityId = timingViewModel.activityId
        timingViewModel = viewModel
        if previousActivityId != viewModel.activityId {
            activeDrawer = nil
            showsLauncher = false
            lastTemporalQuestion = nil
        }
        switch surfaceState {
        case .defaultHome, .needsReview, .syncPending:
            surfaceState = Self.surface(for: viewModel.projection)
        case .expandedTimingRun, .groundedAnswer:
            break
        }
    }

    public func dismissDrawer() {
        activeDrawer = nil
    }

    public func performTemporalNavigation(_ destination: TemporalNavigationDestination) {
        switch destination {
        case .currentRun:
            surfaceState = .expandedTimingRun
            activeDrawer = nil
        case .needsReview:
            surfaceState = .needsReview
            activeDrawer = nil
        case .syncQueue:
            activeDrawer = .syncQueue
        case .askTime:
            activeDrawer = .askTime
        case .close:
            activeDrawer = nil
        }
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
        case .localQueue:
            await performLocalQueueAction(action)
        case .drawer, .navigation, .displayOnly:
            break
        }
        await prepare(route: spec.route)
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
            activeDrawer = .quickCapture
            return
        case .confirmFrictionEvidence:
            guard let resourceName = timingViewModel.detourResourceName,
                  let note = timingViewModel.detourNote
            else {
                activeDrawer = .quickCapture
                return
            }
            await timingViewModel.confirmFrictionEvidence(
                resourceName: resourceName,
                note: note,
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
        case .savePartial:
            await timingViewModel.saveReviewDecision(.savePartial)
        case .activeTimeOnly:
            await timingViewModel.saveReviewDecision(.activeOnly)
        case .frictionEvidenceOnly:
            await timingViewModel.saveReviewDecision(.frictionOnly)
        case .queryEvidenceOnly:
            await timingViewModel.saveReviewDecision(.queryEvidenceOnly)
        case .discardTimingKeepNote:
            await timingViewModel.discardTimingKeepNote()
        case .discardAll:
            await timingViewModel.saveReviewDecision(.discardAll)
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

    public func saveQuickCapture(_ note: String) async {
        let trimmedNote = note.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedNote.isEmpty else { return }
        await timingViewModel.captureTemporalHomeNote(trimmedNote)
        activeDrawer = nil
        refreshSurfaceFromTimingProjection()
    }

    public func submitTemporalQuestion(_ question: String) async {
        let trimmedQuestion = question.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuestion.isEmpty else { return }
        await askTemporalQuestion(trimmedQuestion)
        activeDrawer = nil
        surfaceState = .groundedAnswer
    }

    public func retrySync() async {
        await timingViewModel.retrySyncNow()
        refreshSurfaceFromTimingProjection()
    }

    public func refreshSurfaceFromTimingProjection() {
        switch surfaceState {
        case .defaultHome, .needsReview, .syncPending:
            surfaceState = Self.surface(for: timingViewModel.projection)
        case .expandedTimingRun, .groundedAnswer:
            break
        }
    }

    private func performLocalQueueAction(_ action: TemporalHomeAction) async {
        switch action {
        case .bearerRetryRowSyncPending, .retrySyncPending:
            await retrySync()
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

    private func prepare(route: TemporalHomeRoute) async {
        if route == .drawer(.phase8(.preflightEvidence)) {
            await timingViewModel.refreshPreflightEvidence()
        }
        if route == .drawer(.phase8(.forgottenTimer)) {
            await timingViewModel.refreshForgottenTimerEvidence()
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
            return "How long does \(timingViewModel.activityName) usually take?"
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
