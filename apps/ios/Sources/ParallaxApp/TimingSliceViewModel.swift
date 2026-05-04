import Combine
import Foundation
import ParallaxCore

@MainActor
public final class TimingSliceViewModel: ObservableObject {
    @Published public private(set) var activityName: String
    @Published public private(set) var sessionId: UUID
    @Published public private(set) var status: TimingSessionStatus
    @Published public private(set) var openSpan: TemporalSpanType?
    @Published public private(set) var elapsedSeconds: Int
    @Published public private(set) var activeSeconds: Int
    @Published public private(set) var detourSeconds: Int
    @Published public private(set) var detourNote: String?
    @Published public private(set) var pendingEventCount: Int
    @Published public private(set) var reviewDecision: ModelUpdateDecision?
    @Published public private(set) var errorMessage: String?

    public let activityId: UUID
    public let deviceId: String
    private let eventStore: any PendingTimingEventStore
    private let preflightDecisionStore: any PendingPreflightDecisionStore
    private let now: () -> Date
    private var mutationFactory: MutationEnvelopeFactory
    private var seededMutationFactory = false
    private var startedAt: Date?
    private var completedAt: Date?

    public static let demoPreflightCheckId = UUID(uuidString: "44444444-4444-4444-8444-444444444444")!

    public init(
        activityId: UUID,
        activityName: String,
        sessionId: UUID = UUID(),
        deviceId: String,
        eventStore: any PendingTimingEventStore,
        preflightDecisionStore: any PendingPreflightDecisionStore = InMemoryPendingPreflightDecisionStore(),
        now: @escaping () -> Date = Date.init
    ) {
        self.activityId = activityId
        self.activityName = activityName
        self.sessionId = sessionId
        self.status = .draft
        self.openSpan = nil
        self.elapsedSeconds = 0
        self.activeSeconds = 0
        self.detourSeconds = 0
        self.detourNote = nil
        self.pendingEventCount = 0
        self.reviewDecision = nil
        self.errorMessage = nil
        self.deviceId = deviceId
        self.eventStore = eventStore
        self.preflightDecisionStore = preflightDecisionStore
        self.now = now
        self.mutationFactory = MutationEnvelopeFactory(clientDeviceId: deviceId)
    }

    public static func liveDemo() -> TimingSliceViewModel {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        let parallaxSupport = support.appendingPathComponent("Parallax", isDirectory: true)
        return TimingSliceViewModel(
            activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
            activityName: "Clean pots and pans",
            deviceId: "ios-demo-device",
            eventStore: FilePendingTimingEventStore(
                fileURL: parallaxSupport
                    .appendingPathComponent("pending-timing-events.json")
            ),
            preflightDecisionStore: FilePendingPreflightDecisionStore(
                fileURL: parallaxSupport
                    .appendingPathComponent("pending-preflight-decisions.json")
            )
        )
    }

    public static func reviewedDemo() -> TimingSliceViewModel {
        let model = liveDemo()
        model.status = .reviewed
        model.elapsedSeconds = 1_800
        model.activeSeconds = 1_200
        model.detourSeconds = 600
        model.detourNote = "Had to find the sponge."
        model.pendingEventCount = 4
        model.reviewDecision = .saveUsefulRun
        return model
    }

    public static func runningDemo() -> TimingSliceViewModel {
        let model = liveDemo()
        model.status = .running
        model.openSpan = nil
        model.elapsedSeconds = 734
        model.activeSeconds = 588
        model.detourSeconds = 56
        model.pendingEventCount = 2
        return model
    }

    public var projection: TimingSessionProjection {
        TimingSessionProjection(
            status: status,
            openSpan: openSpan,
            isOffline: false,
            hasPendingSync: pendingEventCount > 0,
            hasUnresolvedInterpretation: detourNote != nil && status == .running,
            needsReview: status == .completedUnreviewed
        )
    }

    public var canStart: Bool {
        status == .draft || status == .abandoned
    }

    public var canRecordDetour: Bool {
        status == .running
    }

    public var canFinish: Bool {
        status == .running || status == .paused
    }

    public var canSaveReview: Bool {
        status == .completedUnreviewed
    }

    public func loadPendingEvents() async {
        _ = await seedMutationFactoryIfNeeded()
    }

    public func startRun() async {
        guard canStart else { return }
        let timestamp = now()
        startedAt = timestamp
        completedAt = nil
        status = .running
        openSpan = nil
        elapsedSeconds = 0
        activeSeconds = 0
        detourSeconds = 0
        detourNote = nil
        reviewDecision = nil
        await appendEvent(.sessionStarted, at: timestamp, payload: ["measurement_mode": MeasurementMode.wholeTask.rawValue])
    }

    public func recordSpongeDetour() async {
        guard canRecordDetour else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        openSpan = .resourceDetour
        detourSeconds = max(detourSeconds, 600)
        detourNote = "Had to find the sponge."
        activeSeconds = max(0, elapsedSeconds - detourSeconds)
        await appendEvent(
            .resourceDetourStarted,
            at: timestamp,
            captureMethod: .quickChip,
            notePreview: detourNote,
            payload: [
                "resource_name": "sponge",
                "count_policy": CountPolicy.wallOnly.rawValue
            ]
        )
    }

    public func confirmSpongeEvidence() async {
        guard status == .running || status == .completedUnreviewed else { return }
        let timestamp = now()
        await appendEvent(
            .extractedEventCreated,
            at: timestamp,
            captureMethod: .quickChip,
            notePreview: "The sponge is gross. I need to go downstairs and get a new one.",
            payload: [
                "confirmation_state": "user_confirmed",
                "span_type": TemporalSpanType.resourceDetour.rawValue,
                "friction_category": "resource",
                "resource_name": "sponge",
                "count_policy": CountPolicy.wallOnly.rawValue,
                "suggested_preflight_text": "Check sponge or scrubber before starting.",
            ]
        )
    }

    public func completeCurrentCheckpoint() async {
        guard status == .running else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        await appendEvent(
            .checkpointCompleted,
            at: timestamp,
            payload: [
                "checkpoint_index": "2",
                "checkpoint_label": "Load dishwasher",
                "elapsed_seconds": "734",
                "active_seconds": "588",
            ]
        )
    }

    public func updateCheckpointPlan() async {
        let timestamp = now()
        await appendEvent(
            .intentRecorded,
            at: timestamp,
            payload: [
                "measurement_mode": MeasurementMode.checkpointed.rawValue,
                "checkpoint_action": "split_hand_wash_pans",
                "checkpoint_label": "Hand-wash pans",
                "sequence_integrity": "preserve_order",
            ]
        )
    }

    public func finishRun() async {
        guard canFinish else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        completedAt = timestamp
        status = .completedUnreviewed
        openSpan = nil
        await appendEvent(.sessionCompleted, at: timestamp, payload: ["source": "first_vertical_slice"])
    }

    public func saveUsefulReview() async {
        await saveReviewDecision(.saveUsefulRun)
    }

    public func saveReviewDecision(_ decision: ModelUpdateDecision) async {
        guard canSaveReview || status == .reviewed else { return }
        if decision.isDiscardDecision {
            await discardReviewDecision(decision)
            return
        }
        let timestamp = now()
        status = .reviewed
        reviewDecision = decision
        let option = ReviewDecisionDisplayFactory.option(for: decision)
        await appendEvent(
            .reviewSaved,
            at: timestamp,
            payload: [
                "decision": decision.rawValue,
                "model_inclusion": option.modelInclusion.rawValue,
                "scopes": option.scopes.map(\.rawValue).joined(separator: ","),
            ]
        )
    }

    public func trimForgottenTimerAtPlaceChange() async {
        guard status == .completedUnreviewed || status == .reviewed else { return }
        let timestamp = now()
        let originalElapsedSeconds = elapsedSeconds
        let originalActiveSeconds = activeSeconds
        elapsedSeconds = min(elapsedSeconds, 2_520)
        activeSeconds = min(activeSeconds, 1_860, elapsedSeconds)
        await appendEvent(
            .userCorrectionApplied,
            at: timestamp,
            payload: [
                "correction_type": "forgotten_timer_place_change",
                "reason_code": "place_changed_after_long_idle_gap",
                "idle_gap_seconds": "2700",
                "original_elapsed_seconds": "\(originalElapsedSeconds)",
                "trimmed_elapsed_seconds": "\(elapsedSeconds)",
                "original_active_seconds": "\(originalActiveSeconds)",
                "trimmed_active_seconds": "\(activeSeconds)",
                "start_place_category": "kitchen",
                "completion_place_category": "store",
                "privacy_display": "human_explanation_only",
            ]
        )
    }

    public func decidePreflightCheck(
        _ decision: PreflightCheckDecision,
        checkId: UUID = TimingSliceViewModel.demoPreflightCheckId,
        snoozedUntil: Date? = nil,
        reason: String? = nil
    ) async {
        guard await seedMutationFactoryIfNeeded() else { return }
        let timestamp = now()
        let mutation = mutationFactory.next(prefix: "decide_preflight_check", at: timestamp)
        let pendingDecision = PendingPreflightDecision(
            activityId: activityId,
            checkId: checkId,
            mutation: mutation,
            decision: decision,
            decidedAt: timestamp,
            snoozedUntil: snoozedUntil,
            reason: reason
        )
        do {
            try await preflightDecisionStore.append(pendingDecision)
            await refreshPendingCount()
            errorMessage = nil
        } catch {
            errorMessage = "Saved on screen, but local preflight queue persistence failed."
        }
    }

    public func timerKeptRunningAfterPlaceChange() async {
        guard status == .completedUnreviewed || status == .reviewed else { return }
        let timestamp = now()
        await appendEvent(
            .reviewSaved,
            at: timestamp,
            payload: [
                "decision": "timer_kept_running",
                "reason_code": "place_change_reviewed",
                "model_inclusion": ModelInclusion.notReviewed.rawValue,
            ]
        )
    }

    private func appendEvent(
        _ eventType: TimingEventType,
        at timestamp: Date,
        captureMethod: CaptureMethod? = .manualButton,
        notePreview: String? = nil,
        payload: [String: String] = [:]
    ) async {
        guard await seedMutationFactoryIfNeeded() else { return }
        let mutation = mutationFactory.next(prefix: eventType.rawValue, at: timestamp)
        let event = PendingTimingEvent(
            sessionId: sessionId,
            eventType: eventType,
            mutation: mutation,
            clientTime: timestamp,
            timerElapsedSeconds: elapsedSeconds,
            timerActiveSeconds: activeSeconds,
            captureMethod: captureMethod,
            notePreview: notePreview,
            payload: payload
        )
        do {
            try await eventStore.append(event)
            await refreshPendingCount()
            errorMessage = nil
        } catch {
            errorMessage = "Saved on screen, but local queue persistence failed."
        }
    }

    private func discardReviewDecision(_ decision: ModelUpdateDecision) async {
        let timestamp = now()
        status = .discarded
        reviewDecision = decision
        await appendEvent(
            .reviewSaved,
            at: timestamp,
            payload: [
                "decision": decision.rawValue,
                "model_inclusion": ModelInclusion.exclude.rawValue,
                "scopes": "",
                "sync_operation": "discard_timing_session",
                "sync_path": "/v1/timing/sessions/\(sessionId.uuidString)/discard",
            ]
        )
    }

    private func seedMutationFactoryIfNeeded() async -> Bool {
        guard !seededMutationFactory else { return true }
        do {
            let timingEvents = try await eventStore.load()
            let preflightDecisions = try await preflightDecisionStore.load()
            let maxSequence = maxPendingSequence(
                timingEvents: timingEvents,
                preflightDecisions: preflightDecisions
            )
            mutationFactory = MutationEnvelopeFactory(
                clientDeviceId: deviceId,
                initialSequence: maxSequence
            )
            pendingEventCount = timingEvents.count + preflightDecisions.count
            seededMutationFactory = true
            errorMessage = nil
            return true
        } catch {
            errorMessage = "Unable to load local sync queue."
            return false
        }
    }

    private func refreshPendingCount() async {
        do {
            let timingEvents = try await eventStore.load()
            let preflightDecisions = try await preflightDecisionStore.load()
            pendingEventCount = timingEvents.count + preflightDecisions.count
        } catch {
            errorMessage = "Unable to refresh local sync queue."
        }
    }

    private func maxPendingSequence(
        timingEvents: [PendingTimingEvent],
        preflightDecisions: [PendingPreflightDecision]
    ) -> Int {
        let timingMax = timingEvents
            .filter { $0.mutation.clientDeviceId == deviceId }
            .map(\.mutation.clientSequence)
            .max() ?? 0
        let preflightMax = preflightDecisions
            .filter { $0.mutation.clientDeviceId == deviceId }
            .map(\.mutation.clientSequence)
            .max() ?? 0
        return max(timingMax, preflightMax)
    }

    private func updateDurations(at timestamp: Date) {
        guard let startedAt else { return }
        elapsedSeconds = max(0, Int(timestamp.timeIntervalSince(startedAt).rounded()))
        activeSeconds = max(0, elapsedSeconds - detourSeconds)
    }
}
