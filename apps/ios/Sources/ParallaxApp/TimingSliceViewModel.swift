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
    @Published public private(set) var lastTemporalQueryAnswer: TemporalQueryAnswerDTO?
    @Published public private(set) var errorMessage: String?

    public let activityId: UUID
    public let deviceId: String
    private let eventStore: any PendingTimingEventStore
    private let preflightDecisionStore: any PendingPreflightDecisionStore
    private let pendingSyncService: PendingSyncService?
    private let pendingSyncContext: PendingSyncContext?
    private let mutationSequenceStore: (any MutationSequenceStore)?
    private let apiClient: ParallaxAPIClient?
    private let now: () -> Date
    private var mutationFactory: MutationEnvelopeFactory
    private var seededMutationFactory = false
    private var startedAt: Date?
    private var completedAt: Date?

    public var currentCheckpointLabel = "Current checkpoint"
    public var nextCheckpointLabel = "Next checkpoint"

    public init(
        activityId: UUID,
        activityName: String,
        sessionId: UUID = UUID(),
        deviceId: String,
        eventStore: any PendingTimingEventStore,
        preflightDecisionStore: any PendingPreflightDecisionStore = InMemoryPendingPreflightDecisionStore(),
        pendingSyncService: PendingSyncService? = nil,
        pendingSyncContext: PendingSyncContext? = nil,
        mutationSequenceStore: (any MutationSequenceStore)? = nil,
        apiClient: ParallaxAPIClient? = nil,
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
        self.lastTemporalQueryAnswer = nil
        self.errorMessage = nil
        self.deviceId = deviceId
        self.eventStore = eventStore
        self.preflightDecisionStore = preflightDecisionStore
        self.pendingSyncService = pendingSyncService
        self.pendingSyncContext = pendingSyncContext
        self.mutationSequenceStore = mutationSequenceStore
        self.apiClient = apiClient
        self.now = now
        self.mutationFactory = MutationEnvelopeFactory(clientDeviceId: deviceId)
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
        await syncPendingIfConfigured()
    }

    public func startRun(mode: MeasurementMode = .wholeTask) async {
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
        lastTemporalQueryAnswer = nil
        await appendEvent(.sessionStarted, at: timestamp, payload: ["measurement_mode": mode.rawValue])
    }

    public func recordResourceDetour(
        resourceName: String,
        note: String,
        durationSeconds: Int = 600
    ) async {
        guard canRecordDetour else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        openSpan = .resourceDetour
        detourSeconds = max(detourSeconds, durationSeconds)
        detourNote = note
        activeSeconds = max(0, elapsedSeconds - detourSeconds)
        await appendEvent(
            .resourceDetourStarted,
            at: timestamp,
            captureMethod: .quickChip,
            notePreview: detourNote,
            payload: [
                "resource_name": resourceName,
                "count_policy": CountPolicy.wallOnly.rawValue
            ]
        )
    }

    public func confirmFrictionEvidence(
        resourceName: String,
        note: String,
        suggestedPreflightText: String?
    ) async {
        guard status == .running || status == .completedUnreviewed else { return }
        let timestamp = now()
        var payload = [
            "confirmation_state": "user_confirmed",
            "span_type": TemporalSpanType.resourceDetour.rawValue,
            "friction_category": "resource",
            "resource_name": resourceName,
            "count_policy": CountPolicy.wallOnly.rawValue,
        ]
        if let suggestedPreflightText {
            payload["suggested_preflight_text"] = suggestedPreflightText
        }
        await appendEvent(
            .extractedEventCreated,
            at: timestamp,
            captureMethod: .quickChip,
            notePreview: note,
            payload: payload
        )
    }

    public func completeCurrentCheckpoint(label: String? = nil) async {
        guard status == .running else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        await appendEvent(
            .checkpointCompleted,
            at: timestamp,
            payload: [
                "checkpoint_index": "2",
                "checkpoint_label": label ?? currentCheckpointLabel,
                "elapsed_seconds": "\(elapsedSeconds)",
                "active_seconds": "\(activeSeconds)",
            ]
        )
    }

    public func pauseCurrentStep() async {
        guard status == .running else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        status = .paused
        openSpan = nil
        await appendEvent(
            .sessionPaused,
            at: timestamp,
            payload: [
                "pause_reason": "user_paused_step",
                "checkpoint_label": currentCheckpointLabel,
            ]
        )
    }

    public func resumeRun() async {
        guard status == .paused else { return }
        let timestamp = now()
        status = .running
        await appendEvent(
            .sessionResumed,
            at: timestamp,
            payload: [
                "resume_reason": "user_resumed_timer",
                "checkpoint_label": currentCheckpointLabel,
            ]
        )
    }

    public func skipCurrentCheckpoint(label: String? = nil) async {
        guard status == .running || status == .paused else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        await appendEvent(
            .checkpointSkipped,
            at: timestamp,
            payload: [
                "checkpoint_index": "2",
                "checkpoint_label": label ?? currentCheckpointLabel,
                "reason": "user_skipped_from_step_drawer",
            ]
        )
    }

    public func moveCurrentCheckpoint(label: String? = nil) async {
        let timestamp = now()
        await appendEvent(
            .scopeChanged,
            at: timestamp,
            payload: [
                "checkpoint_action": "move_current_step",
                "checkpoint_label": label ?? currentCheckpointLabel,
                "sequence_integrity": "preserve_order",
            ]
        )
    }

    public func captureStepNote() async {
        await captureTemporalHomeNote("Note for \(currentCheckpointLabel).")
    }

    public func captureTemporalHomeNote(_ note: String) async {
        let timestamp = now()
        await appendEvent(
            .annotationCaptured,
            at: timestamp,
            captureMethod: .quickChip,
            notePreview: note,
            payload: [
                "input_mode": AnnotationInputMode.quickChip.rawValue,
                "source": "temporal_home",
            ]
        )
    }

    public func correctFrictionEvidence() async {
        let timestamp = now()
        await appendEvent(
            .userCorrectionApplied,
            at: timestamp,
            captureMethod: .quickChip,
            notePreview: "Corrected friction evidence.",
            payload: [
                "correction_type": "extracted_event_corrected",
                "span_type": TemporalSpanType.resourceDetour.rawValue,
                "friction_category": TemporalFrictionCategory.resource.rawValue,
                "count_policy": CountPolicy.wallOnly.rawValue,
            ]
        )
    }

    public func ignoreFrictionEvidence() async {
        let timestamp = now()
        await appendEvent(
            .userCorrectionApplied,
            at: timestamp,
            captureMethod: .quickChip,
            notePreview: "Marked friction evidence as not relevant.",
            payload: [
                "correction_type": "extracted_event_ignored",
                "confirmation_state": ExtractedEventConfirmationState.ignored.rawValue,
                "count_policy": CountPolicy.doNotCount.rawValue,
            ]
        )
    }

    public func keepFrictionNoteOnly() async {
        let timestamp = now()
        await appendEvent(
            .annotationCaptured,
            at: timestamp,
            captureMethod: .reviewReconstruction,
            notePreview: "Keep this note as context only.",
            payload: [
                "model_inclusion": ModelInclusion.queryEvidenceOnly.rawValue,
                "count_policy": CountPolicy.doNotCount.rawValue,
                "source": "friction_evidence_drawer",
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
                "checkpoint_action": "update_checkpoint_plan",
                "checkpoint_label": nextCheckpointLabel,
                "sequence_integrity": "preserve_order",
            ]
        )
    }

    public func makeCheckpointOptional() async {
        let timestamp = now()
        await appendEvent(
            .intentRecorded,
            at: timestamp,
            payload: [
                "checkpoint_action": "make_optional",
                "checkpoint_label": nextCheckpointLabel,
                "sequence_integrity": "skip_without_corrupting_sequence",
            ]
        )
    }

    public func startFromCurrentCheckpoint() async {
        let timestamp = now()
        status = .running
        startedAt = startedAt ?? timestamp
        await appendEvent(
            .checkpointStarted,
            at: timestamp,
            payload: [
                "checkpoint_index": "3",
                "checkpoint_label": nextCheckpointLabel,
                "source": "checkpoint_setup_drawer",
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
                "start_place_category": "start_area",
                "completion_place_category": "later_area",
                "privacy_display": "human_explanation_only",
            ]
        )
    }

    public func decidePreflightCheck(
        _ decision: PreflightCheckDecision,
        checkId: UUID? = nil,
        snoozedUntil: Date? = nil,
        reason: String? = nil
    ) async {
        guard await seedMutationFactoryIfNeeded() else { return }
        guard let checkId else {
            errorMessage = "Choose a real preflight check before saving this decision."
            return
        }
        let timestamp = now()
        let resolvedSnoozedUntil = decision == .snooze
            ? snoozedUntil ?? timestamp.addingTimeInterval(86_400)
            : snoozedUntil
        do {
            let mutation = try await nextMutation(prefix: "decide_preflight_check", at: timestamp)
            let pendingDecision = PendingPreflightDecision(
                activityId: activityId,
                checkId: checkId,
                mutation: mutation,
                decision: decision,
                decidedAt: timestamp,
                snoozedUntil: resolvedSnoozedUntil,
                reason: reason
            )
            try await preflightDecisionStore.append(pendingDecision)
            await refreshPendingCount()
            errorMessage = nil
            await syncPendingIfConfigured()
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

    public func discardTimingKeepNote() async {
        await saveReviewDecision(.discardTimingKeepNote)
    }

    public func deferForgottenTimerDecision() async {
        guard status == .completedUnreviewed || status == .reviewed else { return }
        let timestamp = now()
        await appendEvent(
            .reviewSaved,
            at: timestamp,
            payload: [
                "decision": "forgotten_timer_not_sure",
                "reason_code": "needs_later_review",
                "model_inclusion": ModelInclusion.notReviewed.rawValue,
            ]
        )
    }

    public func submitTemporalQuery(_ question: String) async {
        let timestamp = now()
        lastTemporalQueryAnswer = nil
        if let apiClient, await seedMutationFactoryIfNeeded() {
            do {
                let mutation = try await nextMutation(prefix: "temporal_query", at: timestamp)
                let request = try apiClient.createTemporalQueryRequest(
                    mutation: mutation,
                    question: question,
                    activityId: activityId,
                    includeRawQuotes: false
                )
                lastTemporalQueryAnswer = try await apiClient.send(request, decode: TemporalQueryAnswerDTO.self)
                errorMessage = nil
                return
            } catch {
                errorMessage = "Question saved locally. Backend answer can retry when reachable."
            }
        }
        await appendEvent(
            .intentRecorded,
            at: timestamp,
            captureMethod: .manualButton,
            notePreview: question,
            payload: [
                "workflow": "answer_temporal_query",
                "api_path": "/v1/temporal/query",
                "include_raw_quotes": "false",
            ]
        )
    }

    public func retrySyncNow() async {
        _ = await seedMutationFactoryIfNeeded()
        await syncPendingIfConfigured()
    }

    private func appendEvent(
        _ eventType: TimingEventType,
        at timestamp: Date,
        captureMethod: CaptureMethod? = .manualButton,
        notePreview: String? = nil,
        payload: [String: String] = [:]
    ) async {
        guard await seedMutationFactoryIfNeeded() else { return }
        do {
            let mutation = try await nextMutation(prefix: eventType.rawValue, at: timestamp)
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
            try await eventStore.append(event)
            await refreshPendingCount()
            errorMessage = nil
            await syncPendingIfConfigured()
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
            let persistedSequence = try await mutationSequenceStore?.loadSequence(
                clientDeviceId: deviceId
            ) ?? 0
            let maxSequence = maxPendingSequence(
                timingEvents: timingEvents,
                preflightDecisions: preflightDecisions
            )
            mutationFactory = MutationEnvelopeFactory(
                clientDeviceId: deviceId,
                initialSequence: max(maxSequence, persistedSequence)
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

    private func nextMutation(prefix: String, at timestamp: Date) async throws -> MutationEnvelope {
        let mutation = mutationFactory.next(prefix: prefix, at: timestamp)
        try await mutationSequenceStore?.saveSequence(
            mutation.clientSequence,
            clientDeviceId: deviceId
        )
        return mutation
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

    private func syncPendingIfConfigured() async {
        guard let pendingSyncService, let pendingSyncContext else { return }
        do {
            _ = try await pendingSyncService.sync(context: pendingSyncContext)
            await refreshPendingCount()
            errorMessage = nil
        } catch {
            await refreshPendingCount()
            errorMessage = "Saved locally. Sync will retry when the backend is reachable."
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
