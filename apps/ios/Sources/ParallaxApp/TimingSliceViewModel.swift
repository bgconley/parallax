import Combine
import Foundation
import ParallaxCore

public struct SyncQueueRowProjection: Equatable, Sendable {
    public let title: String
    public let detail: String
    public let role: TemporalSemanticRole

    public init(title: String, detail: String, role: TemporalSemanticRole) {
        self.title = title
        self.detail = detail
        self.role = role
    }
}

public struct ForgottenTimerEvidenceProjection: Equatable, Sendable {
    public let eyebrow: String
    public let title: String
    public let subtitle: String
    public let evidenceTitle: String
    public let evidenceLines: [String]
    public let chips: [String]
    public let primaryFlagId: UUID?
    public let canTrim: Bool
    public let canResolveKeptRunning: Bool
    public let canDefer: Bool

    public init(
        eyebrow: String,
        title: String,
        subtitle: String,
        evidenceTitle: String,
        evidenceLines: [String],
        chips: [String],
        primaryFlagId: UUID?,
        canTrim: Bool,
        canResolveKeptRunning: Bool,
        canDefer: Bool
    ) {
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.evidenceTitle = evidenceTitle
        self.evidenceLines = evidenceLines
        self.chips = chips
        self.primaryFlagId = primaryFlagId
        self.canTrim = canTrim
        self.canResolveKeptRunning = canResolveKeptRunning
        self.canDefer = canDefer
    }

    public static func none(reason: String = "No open forgotten-timer review flag.") -> ForgottenTimerEvidenceProjection {
        ForgottenTimerEvidenceProjection(
            eyebrow: "Review flag · no active prompt",
            title: "No forgotten timer flag",
            subtitle: "Parallax only trims or resolves a forgotten timer prompt when backend evidence exists.",
            evidenceTitle: "What Parallax knows",
            evidenceLines: [
                reason,
                "No source timing facts will change from this drawer.",
                "Complete a run and review context to create a prompt.",
            ],
            chips: ["no flag", "no change", "safe"],
            primaryFlagId: nil,
            canTrim: false,
            canResolveKeptRunning: false,
            canDefer: false
        )
    }

    public var homeRowTitle: String {
        primaryFlagId == nil ? "Forgotten timer" : title
    }

    public var homeRowDetail: String {
        evidenceLines.first ?? subtitle
    }

    public static func make(flags: [TimingReviewFlagDTO]) -> ForgottenTimerEvidenceProjection {
        guard let flag = flags.first(where: { ($0.status ?? .open) == .open }) ?? flags.first else {
            return .none()
        }
        let message = flag.userMessage ?? "Review whether this timer kept running longer than intended."
        let reason = ParallaxDisplayText.humanizeIdentifier(flag.reasonCode ?? "review_prompt")
        let severity = ParallaxDisplayText.humanizeIdentifier(flag.severity ?? "review")
        let confidence = flag.confidence.map { String(format: "confidence %.2f", $0) } ?? "confidence unavailable"
        let status = flag.status?.displayText ?? "Open"
        let flagType = ParallaxDisplayText.humanizeIdentifier(flag.flagType ?? "possible_forgotten_timer")
        let isActionable = flag.status == nil || flag.status == .open
        return ForgottenTimerEvidenceProjection(
            eyebrow: "Review flag · \(flagType)",
            title: "Timer may have kept running?",
            subtitle: "Choose what happened. Prompt resolution is separate from timing correction.",
            evidenceTitle: "Why I am asking",
            evidenceLines: [
                message,
                "Reason: \(reason)",
                "\(severity) · \(confidence)",
            ],
            chips: [status, "Human choice", "Private"],
            primaryFlagId: flag.id,
            canTrim: isActionable,
            canResolveKeptRunning: isActionable,
            canDefer: isActionable
        )
    }
}

public struct PreflightEvidenceProjection: Equatable, Sendable {
    public let title: String
    public let subtitle: String
    public let evidenceTitle: String
    public let evidenceLines: [String]
    public let chips: [String]
    public let noteTitle: String
    public let noteLines: [String]
    public let primaryCheckId: UUID?
    public let hasBackendEvidence: Bool

    public init(
        title: String,
        subtitle: String,
        evidenceTitle: String,
        evidenceLines: [String],
        chips: [String],
        noteTitle: String,
        noteLines: [String],
        primaryCheckId: UUID?,
        hasBackendEvidence: Bool
    ) {
        self.title = title
        self.subtitle = subtitle
        self.evidenceTitle = evidenceTitle
        self.evidenceLines = evidenceLines
        self.chips = chips
        self.noteTitle = noteTitle
        self.noteLines = noteLines
        self.primaryCheckId = primaryCheckId
        self.hasBackendEvidence = hasBackendEvidence
    }

    public static func none(activityName: String, reason: String = "No backend preflight checks yet.") -> PreflightEvidenceProjection {
        PreflightEvidenceProjection(
            title: "No preflight evidence yet",
            subtitle: "Repeated confirmed friction for \(activityName) will surface checks here.",
            evidenceTitle: "What Parallax knows",
            evidenceLines: [
                reason,
                "Resource dependency count is 0.",
                "No preflight decision will be saved without a real check.",
            ],
            chips: ["no evidence", "no change", "review first"],
            noteTitle: "How to build evidence",
            noteLines: ["Log friction during a run, then review it before learning."],
            primaryCheckId: nil,
            hasBackendEvidence: false
        )
    }

    public static func make(
        activityName: String,
        checks: [PreflightCheckDTO],
        resourceDependencies: [ResourceDependencyDTO],
        latestDetourNote: String?
    ) -> PreflightEvidenceProjection {
        let actionableCheck = checks.first { ($0.state ?? "suggested") != "retired" && ($0.state ?? "suggested") != "hidden" }
            ?? checks.first
        let dependency = resourceDependencies.first
        guard actionableCheck != nil || dependency != nil else {
            return .none(activityName: activityName)
        }

        let source = ParallaxDisplayText.humanizeIdentifier(actionableCheck?.source ?? "resource_dependency")
        let state = actionableCheck?.state ?? "suggested"
        let stateLabel = ParallaxDisplayText.humanizeIdentifier(state)
        let failureCountValue = dependency?.failureCount ?? actionableCheck?.failureCount ?? actionableCheck?.evidenceCount
        let confidenceValue = dependency?.confidence ?? actionableCheck?.confidence
        let failureCount = failureCountValue.map { "Failure count \($0)" } ?? "Failure count not available"
        let confidence = confidenceValue.map { String(format: "confidence %.2f", $0) } ?? "confidence not available"
        let resourceName = dependency?.resourceName ?? actionableCheck?.evidenceSummary ?? "preflight evidence"
        let noteLine = latestDetourNote.map { "Latest local note: \($0)" }
            ?? actionableCheck?.evidenceSummary
            ?? "Raw matching notes stay hidden unless privacy settings allow them."

        return PreflightEvidenceProjection(
            title: actionableCheck?.checkText ?? "Review resource dependency",
            subtitle: "Suggested only after confirmed friction appears across reviewed runs.",
            evidenceTitle: "Why I am suggesting this",
            evidenceLines: [
                "Source: \(source)",
                "\(failureCount) · \(confidence)",
                "Resource: \(resourceName)",
            ],
            chips: [stateLabel, "Can snooze", "Can hide", "Can retire"],
            noteTitle: "Last matching note",
            noteLines: [noteLine],
            primaryCheckId: actionableCheck?.id,
            hasBackendEvidence: true
        )
    }
}

public struct FrictionEvidenceProjection: Equatable, Sendable {
    public let eyebrow: String
    public let title: String
    public let subtitle: String
    public let evidenceTitle: String
    public let evidenceLines: [String]
    public let chips: [String]
    public let learningTitle: String
    public let learningLines: [String]
    public let canConfirm: Bool
    public let canCorrect: Bool
    public let canIgnore: Bool
    public let canKeepNoteOnly: Bool

    public init(
        eyebrow: String,
        title: String,
        subtitle: String,
        evidenceTitle: String,
        evidenceLines: [String],
        chips: [String],
        learningTitle: String,
        learningLines: [String],
        canConfirm: Bool,
        canCorrect: Bool,
        canIgnore: Bool,
        canKeepNoteOnly: Bool
    ) {
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.evidenceTitle = evidenceTitle
        self.evidenceLines = evidenceLines
        self.chips = chips
        self.learningTitle = learningTitle
        self.learningLines = learningLines
        self.canConfirm = canConfirm
        self.canCorrect = canCorrect
        self.canIgnore = canIgnore
        self.canKeepNoteOnly = canKeepNoteOnly
    }

    public static func none(activityName: String) -> FrictionEvidenceProjection {
        FrictionEvidenceProjection(
            eyebrow: "No captured friction yet",
            title: "No friction evidence yet",
            subtitle: "Log friction during an active run before correcting or confirming detours.",
            evidenceTitle: "What Parallax knows",
            evidenceLines: [
                "No resource blocker has been captured for \(activityName).",
                "No friction correction will be saved without user evidence.",
                "Friction evidence starts from a user-authored note.",
            ],
            chips: ["no evidence", "no change", "log first"],
            learningTitle: "Learning effect",
            learningLines: ["Repeated confirmed detours can become a preflight check."],
            canConfirm: false,
            canCorrect: false,
            canIgnore: false,
            canKeepNoteOnly: false
        )
    }

    public static func make(
        resourceName: String?,
        note: String?,
        activityName: String
    ) -> FrictionEvidenceProjection {
        let trimmedResource = resourceName?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let trimmedNote = note?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !trimmedResource.isEmpty || !trimmedNote.isEmpty else {
            return .none(activityName: activityName)
        }

        let resourceTitle = trimmedResource.isEmpty ? "Captured friction note" : trimmedResource
        var evidenceLines = [
            "Resource/blocker: \(resourceTitle)",
            "Counts as wall time only, not active work.",
            "Preflight checks require repeated confirmed evidence.",
        ]
        if !trimmedNote.isEmpty {
            evidenceLines.insert(trimmedNote, at: 1)
        }

        return FrictionEvidenceProjection(
            eyebrow: "User-captured friction evidence",
            title: resourceTitle,
            subtitle: "Review the captured note and decide whether it explains wall time.",
            evidenceTitle: "Captured as resource detour",
            evidenceLines: evidenceLines,
            chips: ["resource", "wall only", "user evidence"],
            learningTitle: "Learning effect",
            learningLines: ["Repeated confirmed detours can become a preflight check."],
            canConfirm: true,
            canCorrect: true,
            canIgnore: true,
            canKeepNoteOnly: true
        )
    }
}

public struct StepDetailProjection: Equatable, Sendable {
    public let eyebrow: String
    public let title: String
    public let subtitle: String
    public let summaryTitle: String
    public let summaryLines: [String]
    public let chips: [String]
    public let nextTitle: String
    public let nextLines: [String]
    public let canCompleteStep: Bool
    public let canPause: Bool
    public let canSkip: Bool
    public let canMove: Bool
    public let canAddNote: Bool

    public init(
        eyebrow: String,
        title: String,
        subtitle: String,
        summaryTitle: String,
        summaryLines: [String],
        chips: [String],
        nextTitle: String,
        nextLines: [String],
        canCompleteStep: Bool,
        canPause: Bool,
        canSkip: Bool,
        canMove: Bool,
        canAddNote: Bool
    ) {
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.summaryTitle = summaryTitle
        self.summaryLines = summaryLines
        self.chips = chips
        self.nextTitle = nextTitle
        self.nextLines = nextLines
        self.canCompleteStep = canCompleteStep
        self.canPause = canPause
        self.canSkip = canSkip
        self.canMove = canMove
        self.canAddNote = canAddNote
    }
}

public struct ExpandedTimingRunReviewProjection: Equatable, Sendable {
    public let title: String
    public let detail: String
    public let role: TemporalSemanticRole

    public init(title: String, detail: String, role: TemporalSemanticRole) {
        self.title = title
        self.detail = detail
        self.role = role
    }
}

@MainActor
public final class TimingSliceViewModel: ObservableObject {
    @Published public private(set) var activityName: String
    @Published public private(set) var sessionId: UUID
    @Published public private(set) var measurementMode: MeasurementMode
    @Published public private(set) var status: TimingSessionStatus
    @Published public private(set) var openSpan: TemporalSpanType?
    @Published public private(set) var elapsedSeconds: Int
    @Published public private(set) var activeSeconds: Int
    @Published public private(set) var detourSeconds: Int
    @Published public private(set) var detourNote: String?
    @Published public private(set) var detourResourceName: String?
    @Published public private(set) var pendingEventCount: Int
    @Published public private(set) var pendingSyncRows: [SyncQueueRowProjection]
    @Published public private(set) var reviewDecision: ModelUpdateDecision?
    @Published public private(set) var lastTemporalQueryAnswer: TemporalQueryAnswerDTO?
    @Published public private(set) var preflightEvidence: PreflightEvidenceProjection
    @Published public private(set) var forgottenTimerEvidence: ForgottenTimerEvidenceProjection
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
    private var activeSegmentStartedAt: Date?
    private var accumulatedActiveSeconds = 0
    private var detourStartedAt: Date?
    private var accumulatedDetourSeconds = 0
    private var syncedSessionId: UUID?

    @Published public private(set) var currentCheckpointLabel = "Current checkpoint"
    @Published public private(set) var nextCheckpointLabel = "Next checkpoint"
    private var currentCheckpointSequenceOrder = 2

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
        self.measurementMode = .wholeTask
        self.status = .draft
        self.openSpan = nil
        self.elapsedSeconds = 0
        self.activeSeconds = 0
        self.detourSeconds = 0
        self.detourNote = nil
        self.detourResourceName = nil
        self.pendingEventCount = 0
        self.pendingSyncRows = []
        self.reviewDecision = nil
        self.lastTemporalQueryAnswer = nil
        self.preflightEvidence = .none(activityName: activityName)
        self.forgottenTimerEvidence = .none()
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
        status == .draft || status == .intentRecorded || status == .abandoned || status == .reviewed || status == .discarded
    }

    public var canRecordDetour: Bool {
        status == .running
    }

    public var isCheckpointedMode: Bool {
        measurementMode == .checkpointed || measurementMode == .routine
    }

    public var canFinish: Bool {
        status == .running || status == .paused
    }

    public var canSaveReview: Bool {
        status == .completedUnreviewed
    }

    public var stepDetail: StepDetailProjection {
        let statusText = status.displayText
        let modeText = measurementMode.displayText
        guard status == .running || status == .paused else {
            return StepDetailProjection(
                eyebrow: "No active checkpoint",
                title: "No run in progress",
                subtitle: "Start a timer before waiting, pause, or checkpoint actions become available.",
                summaryTitle: "Current activity",
                summaryLines: [
                    activityName,
                "Mode: \(modeText)",
                "No timing event will be saved from this drawer.",
                ],
                chips: ["ready", "no run", "no change"],
                nextTitle: "Next action",
                nextLines: ["Start a run from Temporal Home to capture waiting or pause evidence."],
                canCompleteStep: false,
                canPause: false,
                canSkip: false,
                canMove: false,
                canAddNote: false
            )
        }

        if isCheckpointedMode {
            return StepDetailProjection(
                eyebrow: "Current checkpoint · \(statusText)",
                title: currentCheckpointLabel,
                subtitle: "Checkpoint labels stay optional; this marker can still teach timing.",
                summaryTitle: "What this checkpoint is showing",
                summaryLines: [
                    "Active work and elapsed time stay separate",
                    "Setup, pause, and friction can be reviewed",
                    "Count policy remains explicit",
                ],
                chips: ["active checkpoint", "checkpointed", "moveable"],
                nextTitle: "Next checkpoint",
                nextLines: ["Predictions appear after reviewed evidence exists"],
                canCompleteStep: status == .running,
                canPause: status == .running,
                canSkip: true,
                canMove: true,
                canAddNote: true
            )
        }

        return StepDetailProjection(
            eyebrow: "Whole-task run · \(statusText)",
            title: activityName,
            subtitle: "Waiting and pause apply to this run; checkpoint actions require checkpointed mode.",
            summaryTitle: "What this run is showing",
            summaryLines: [
                "Wall and active time stay separate",
                "Pause preserves wall time without active work",
                "Checkpoint complete, skip, and move stay unavailable",
            ],
            chips: [status.displayText, "Whole task", "No checkpoint"],
            nextTitle: "Next review",
            nextLines: ["Finish the run, then review what should update the model."],
            canCompleteStep: false,
            canPause: status == .running,
            canSkip: false,
            canMove: false,
            canAddNote: true
        )
    }

    public var frictionEvidence: FrictionEvidenceProjection {
        FrictionEvidenceProjection.make(
            resourceName: detourResourceName,
            note: detourNote,
            activityName: activityName
        )
    }

    public var expandedRunReviewProjection: ExpandedTimingRunReviewProjection {
        switch status {
        case .completedUnreviewed:
            return ExpandedTimingRunReviewProjection(
                title: "Review ready",
                detail: "model inclusion pending",
                role: .waiting
            )
        case .reviewed:
            return ExpandedTimingRunReviewProjection(
                title: "Reviewed",
                detail: reviewDecision.map { ReviewDecisionDisplayFactory.option(for: $0).title } ?? "Model inclusion saved",
                role: .active
            )
        case .discarded:
            return ExpandedTimingRunReviewProjection(
                title: "Discarded",
                detail: "excluded from timing model",
                role: .interruption
            )
        case .running:
            return ExpandedTimingRunReviewProjection(
                title: "Run in progress",
                detail: "finish before review",
                role: .active
            )
        case .paused:
            return ExpandedTimingRunReviewProjection(
                title: "Timer paused",
                detail: "resume or finish before review",
                role: .waiting
            )
        case .draft, .intentRecorded, .abandoned:
            return ExpandedTimingRunReviewProjection(
                title: "No review yet",
                detail: "start timing first",
                role: .wall
            )
        }
    }

    public func loadPendingEvents() async {
        _ = await seedMutationFactoryIfNeeded()
        await syncPendingIfConfigured()
    }

    public func refreshPreflightEvidence() async {
        guard let apiClient else {
            preflightEvidence = .none(activityName: activityName, reason: "Backend profile is not connected.")
            return
        }
        do {
            let checksRequest = try apiClient.listPreflightChecksRequest(activityId: activityId)
            let dependencyRequest = try apiClient.listResourceDependenciesRequest(activityId: activityId)
            let checks: [PreflightCheckDTO] = try await apiClient.send(checksRequest, decode: [PreflightCheckDTO].self)
            let dependencies: [ResourceDependencyDTO] = try await apiClient.send(dependencyRequest, decode: [ResourceDependencyDTO].self)
            preflightEvidence = PreflightEvidenceProjection.make(
                activityName: activityName,
                checks: checks,
                resourceDependencies: dependencies,
                latestDetourNote: detourNote
            )
            errorMessage = nil
        } catch {
            preflightEvidence = .none(activityName: activityName, reason: "Backend evidence is unavailable.")
            errorMessage = "Unable to load preflight evidence."
        }
    }

    public func refreshForgottenTimerEvidence() async {
        guard let apiClient else {
            forgottenTimerEvidence = .none(reason: "Backend review flags are not connected.")
            return
        }
        do {
            let request = try apiClient.listTimingReviewFlagsRequest(sessionId: serverSessionId, status: .open)
            let flags = try await apiClient.send(request, decode: [TimingReviewFlagDTO].self)
            forgottenTimerEvidence = .make(flags: flags)
            errorMessage = nil
        } catch {
            forgottenTimerEvidence = .none(reason: "Backend review flags are unavailable.")
            errorMessage = "Unable to load forgotten timer evidence."
        }
    }

    public func startRun(mode: MeasurementMode = .wholeTask) async {
        guard canStart else { return }
        if status == .reviewed || status == .discarded || status == .abandoned {
            prepareNewRunShell()
        }
        let timestamp = now()
        measurementMode = mode
        resetCheckpointProjection()
        startedAt = timestamp
        completedAt = nil
        status = .running
        openSpan = nil
        elapsedSeconds = 0
        activeSeconds = 0
        detourSeconds = 0
        activeSegmentStartedAt = timestamp
        accumulatedActiveSeconds = 0
        detourStartedAt = nil
        accumulatedDetourSeconds = 0
        detourNote = nil
        detourResourceName = nil
        reviewDecision = nil
        lastTemporalQueryAnswer = nil
        await appendEvent(.sessionStarted, at: timestamp, payload: ["measurement_mode": mode.rawValue])
        if isCheckpointedMode {
            await appendEvent(
                .checkpointStarted,
                at: timestamp,
                payload: currentCheckpointPayload().merging([
                    "source": "timing_launcher",
                ]) { _, new in new }
            )
        }
    }

    private func prepareNewRunShell() {
        sessionId = UUID()
        syncedSessionId = nil
        measurementMode = .wholeTask
        status = .draft
        openSpan = nil
        elapsedSeconds = 0
        activeSeconds = 0
        detourSeconds = 0
        detourNote = nil
        detourResourceName = nil
        reviewDecision = nil
        forgottenTimerEvidence = .none()
        startedAt = nil
        completedAt = nil
        activeSegmentStartedAt = nil
        accumulatedActiveSeconds = 0
        detourStartedAt = nil
        accumulatedDetourSeconds = 0
        errorMessage = nil
        resetCheckpointProjection()
    }

    private func resetCheckpointProjection() {
        currentCheckpointSequenceOrder = 2
        currentCheckpointLabel = "Current checkpoint"
        nextCheckpointLabel = "Next checkpoint"
    }

    private func currentCheckpointPayload(label: String? = nil) -> [String: String] {
        let resolvedLabel = label ?? currentCheckpointLabel
        return [
            "sequence_order": "\(currentCheckpointSequenceOrder)",
            "label": resolvedLabel,
            "checkpoint_index": "\(currentCheckpointSequenceOrder)",
            "checkpoint_label": resolvedLabel,
        ]
    }

    private func advanceCheckpointProjection() {
        currentCheckpointSequenceOrder += 1
        currentCheckpointLabel = nextCheckpointLabel
        nextCheckpointLabel = "Checkpoint \(currentCheckpointSequenceOrder + 1)"
    }

    public func refreshTimer() {
        guard status == .running || status == .paused else { return }
        updateDurations(at: now())
    }

    public func recordResourceDetour(
        resourceName: String,
        note: String,
        durationSeconds: Int? = nil
    ) async {
        guard canRecordDetour else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        accumulatedActiveSeconds = activeSeconds
        activeSegmentStartedAt = nil
        let trimmedResourceName = resourceName.trimmingCharacters(in: .whitespacesAndNewlines)
        detourResourceName = trimmedResourceName.isEmpty ? "user-entered friction" : trimmedResourceName
        detourNote = note
        if let durationSeconds, durationSeconds > 0 {
            accumulatedDetourSeconds += durationSeconds
            detourSeconds = accumulatedDetourSeconds
            openSpan = nil
            activeSegmentStartedAt = timestamp
        } else {
            openSpan = .resourceDetour
            detourStartedAt = timestamp
        }
        await appendEvent(
            .resourceDetourStarted,
            at: timestamp,
            captureMethod: .quickChip,
            notePreview: detourNote,
            payload: [
                "resource_name": detourResourceName ?? "user-entered friction",
                "count_policy": CountPolicy.wallOnly.rawValue
            ]
        )
    }

    public func logFriction(resourceName: String, note: String) async {
        let trimmedNote = note.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedNote.isEmpty else {
            errorMessage = "Add a short note before saving friction."
            return
        }
        let trimmedResource = resourceName.trimmingCharacters(in: .whitespacesAndNewlines)
        await captureTemporalHomeNote(
            trimmedNote,
            source: "timing_session_friction",
            captureMethod: .manualButton
        )
        await recordResourceDetour(
            resourceName: trimmedResource.isEmpty ? "user-entered friction" : trimmedResource,
            note: trimmedNote
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
        guard status == .running, isCheckpointedMode else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        let payload = currentCheckpointPayload(label: label)
        await appendEvent(
            .checkpointCompleted,
            at: timestamp,
            payload: payload.merging([
                "elapsed_seconds": "\(elapsedSeconds)",
                "active_seconds": "\(activeSeconds)",
            ]) { _, new in new }
        )
        advanceCheckpointProjection()
        await appendEvent(
            .checkpointStarted,
            at: timestamp,
            payload: currentCheckpointPayload().merging([
                "source": "checkpoint_auto_advance",
            ]) { _, new in new }
        )
    }

    public func pauseCurrentStep() async {
        guard status == .running else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        accumulatedActiveSeconds = activeSeconds
        accumulatedDetourSeconds = detourSeconds
        status = .paused
        activeSegmentStartedAt = nil
        detourStartedAt = nil
        await appendEvent(
            .sessionPaused,
            at: timestamp,
            payload: [
                "pause_reason": "user_paused_step",
                "checkpoint_label": isCheckpointedMode ? currentCheckpointLabel : activityName,
            ]
        )
    }

    public func resumeRun() async {
        guard status == .paused else { return }
        let timestamp = now()
        status = .running
        if openSpan == .resourceDetour {
            detourStartedAt = timestamp
        } else {
            activeSegmentStartedAt = timestamp
        }
        await appendEvent(
            .sessionResumed,
            at: timestamp,
            payload: [
                "resume_reason": "user_resumed_timer",
                "checkpoint_label": isCheckpointedMode ? currentCheckpointLabel : activityName,
            ]
        )
    }

    public func skipCurrentCheckpoint(label: String? = nil) async {
        guard (status == .running || status == .paused), isCheckpointedMode else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        let payload = currentCheckpointPayload(label: label)
        await appendEvent(
            .checkpointSkipped,
            at: timestamp,
            payload: payload.merging([
                "reason": "user_skipped_from_step_drawer",
            ]) { _, new in new }
        )
        advanceCheckpointProjection()
        if status == .running {
            await appendEvent(
                .checkpointStarted,
                at: timestamp,
                payload: currentCheckpointPayload().merging([
                    "source": "checkpoint_auto_advance",
                ]) { _, new in new }
            )
        }
    }

    public func moveCurrentCheckpoint(label: String? = nil) async {
        guard isCheckpointedMode else { return }
        let timestamp = now()
        let payload = currentCheckpointPayload(label: label)
        await appendEvent(
            .scopeChanged,
            at: timestamp,
            payload: payload.merging([
                "checkpoint_action": "move_current_step",
                "sequence_integrity": "preserve_order",
            ]) { _, new in new }
        )
    }

    public func captureStepNote(_ note: String) async {
        let checkpointPayload = isCheckpointedMode ? currentCheckpointPayload() : [:]
        await captureTemporalHomeNote(
            note,
            source: "timing_session_step_note",
            captureMethod: .manualButton,
            additionalPayload: checkpointPayload
        )
    }

    public func captureTemporalHomeNote(
        _ note: String,
        source: String = "temporal_home",
        captureMethod: CaptureMethod = .quickChip,
        additionalPayload: [String: String] = [:]
    ) async {
        let trimmedNote = note.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedNote.isEmpty else {
            errorMessage = "Add a short note before saving timing evidence."
            return
        }
        let timestamp = now()
        let inputMode = annotationInputMode(for: captureMethod)
        let payload = [
            "input_mode": inputMode.rawValue,
            "source": source,
        ].merging(additionalPayload) { current, _ in current }
        await appendEvent(
            .annotationCaptured,
            at: timestamp,
            captureMethod: captureMethod,
            notePreview: trimmedNote,
            payload: payload
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
        if canStart {
            await startCheckpointedRunFromSetup()
            return
        }
        guard (status == .running || status == .paused), isCheckpointedMode else { return }
        let timestamp = now()
        let sequenceOrder = currentCheckpointSequenceOrder + 1
        let label = nextCheckpointLabel
        await appendEvent(
            .checkpointStarted,
            at: timestamp,
            payload: [
                "sequence_order": "\(sequenceOrder)",
                "label": label,
                "checkpoint_index": "\(sequenceOrder)",
                "checkpoint_label": label,
                "source": "checkpoint_setup_drawer",
            ]
        )
        currentCheckpointSequenceOrder = sequenceOrder
        currentCheckpointLabel = label
        nextCheckpointLabel = "Checkpoint \(sequenceOrder + 1)"
    }

    private func startCheckpointedRunFromSetup() async {
        if status == .reviewed || status == .discarded || status == .abandoned {
            prepareNewRunShell()
        }
        let timestamp = now()
        let sequenceOrder = currentCheckpointSequenceOrder + 1
        let label = nextCheckpointLabel
        measurementMode = .checkpointed
        startedAt = timestamp
        completedAt = nil
        status = .running
        openSpan = nil
        elapsedSeconds = 0
        activeSeconds = 0
        detourSeconds = 0
        activeSegmentStartedAt = timestamp
        accumulatedActiveSeconds = 0
        detourStartedAt = nil
        accumulatedDetourSeconds = 0
        detourNote = nil
        detourResourceName = nil
        reviewDecision = nil
        lastTemporalQueryAnswer = nil
        await appendEvent(
            .sessionStarted,
            at: timestamp,
            payload: [
                "measurement_mode": MeasurementMode.checkpointed.rawValue,
                "source": "checkpoint_setup_drawer",
            ]
        )
        await appendEvent(
            .checkpointStarted,
            at: timestamp,
            payload: [
                "sequence_order": "\(sequenceOrder)",
                "label": label,
                "checkpoint_index": "\(sequenceOrder)",
                "checkpoint_label": label,
                "source": "checkpoint_setup_drawer",
            ]
        )
        currentCheckpointSequenceOrder = sequenceOrder
        currentCheckpointLabel = label
        nextCheckpointLabel = "Checkpoint \(sequenceOrder + 1)"
    }

    public func finishRun() async {
        guard canFinish else { return }
        let timestamp = now()
        updateDurations(at: timestamp)
        accumulatedActiveSeconds = activeSeconds
        accumulatedDetourSeconds = detourSeconds
        activeSegmentStartedAt = nil
        detourStartedAt = nil
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
        guard !(status == .reviewed && reviewDecision == decision) else { return }
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
        await updateForgottenTimerFlag(
            status: .resolved,
            resolutionNote: "Trimmed at place change.",
            at: timestamp
        )
    }

    public func decidePreflightCheck(
        _ decision: PreflightCheckDecision,
        checkId: UUID? = nil,
        snoozedUntil: Date? = nil,
        reason: String? = nil
    ) async {
        guard await seedMutationFactoryIfNeeded() else { return }
        guard let resolvedCheckId = checkId ?? preflightEvidence.primaryCheckId else {
            errorMessage = "Choose a real preflight check before saving this decision."
            return
        }
        let remoteCheckId = preflightEvidence.hasBackendEvidence
            && resolvedCheckId == preflightEvidence.primaryCheckId
            ? resolvedCheckId
            : nil
        let timestamp = now()
        let resolvedSnoozedUntil = decision == .snooze
            ? snoozedUntil ?? timestamp.addingTimeInterval(86_400)
            : snoozedUntil
        do {
            let mutation = try await nextMutation(prefix: "decide_preflight_check", at: timestamp)
            let pendingDecision = PendingPreflightDecision(
                activityId: activityId,
                checkId: resolvedCheckId,
                remoteCheckId: remoteCheckId,
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
        await updateForgottenTimerFlag(
            status: .resolved,
            resolutionNote: "Timer kept running; source timing facts preserved.",
            at: timestamp
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
        await updateForgottenTimerFlag(
            status: .snoozed,
            resolutionNote: "User deferred forgotten timer decision.",
            at: timestamp
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

    private func updateForgottenTimerFlag(
        status: TimingReviewFlagStatus,
        resolutionNote: String,
        at timestamp: Date
    ) async {
        guard let flagId = forgottenTimerEvidence.primaryFlagId else { return }
        guard let apiClient, await seedMutationFactoryIfNeeded() else { return }
        do {
            let mutation = try await nextMutation(prefix: "update_timing_review_flag", at: timestamp)
            let request = try apiClient.updateTimingReviewFlagRequest(
                flagId: flagId,
                mutation: mutation,
                status: status,
                resolutionNote: resolutionNote
            )
            let updatedFlag = try await apiClient.send(request, decode: TimingReviewFlagDTO.self)
            forgottenTimerEvidence = .make(flags: [updatedFlag])
            errorMessage = nil
        } catch {
            errorMessage = "Saved locally, but review flag update could not sync."
        }
    }

    private var serverSessionId: UUID {
        syncedSessionId ?? sessionId
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
            pendingSyncRows = makePendingSyncRows(
                timingEvents: timingEvents,
                preflightDecisions: preflightDecisions
            )
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
            pendingSyncRows = makePendingSyncRows(
                timingEvents: timingEvents,
                preflightDecisions: preflightDecisions
            )
        } catch {
            errorMessage = "Unable to refresh local sync queue."
        }
    }

    private func syncPendingIfConfigured() async {
        guard let pendingSyncService, let pendingSyncContext else { return }
        do {
            let result = try await pendingSyncService.sync(context: pendingSyncContext)
            if let remoteSessionId = result.remoteSessionIdsByLocalSessionId[sessionId] {
                syncedSessionId = remoteSessionId
            }
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

    private func makePendingSyncRows(
        timingEvents: [PendingTimingEvent],
        preflightDecisions: [PendingPreflightDecision]
    ) -> [SyncQueueRowProjection] {
        enum PendingItem {
            case timing(PendingTimingEvent)
            case preflight(PendingPreflightDecision)

            var sequence: Int {
                switch self {
                case let .timing(event):
                    return event.mutation.clientSequence
                case let .preflight(decision):
                    return decision.mutation.clientSequence
                }
            }
        }

        let items = timingEvents.map(PendingItem.timing) + preflightDecisions.map(PendingItem.preflight)
        return items.sorted { $0.sequence < $1.sequence }.map { item in
            switch item {
            case let .timing(event):
                return SyncQueueRowProjection(
                    title: event.eventType.displayText,
                    detail: "Sync item \(event.mutation.clientSequence)",
                    role: semanticRole(for: event.eventType)
                )
            case let .preflight(decision):
                return SyncQueueRowProjection(
                    title: "Preflight: \(decision.decision.displayText)",
                    detail: "Sync item \(decision.mutation.clientSequence)",
                    role: .waiting
                )
            }
        }
    }

    private func semanticRole(for eventType: TimingEventType) -> TemporalSemanticRole {
        switch eventType {
        case .sessionStarted, .sessionResumed, .activeWorkStarted, .activeWorkCompleted:
            return .active
        case .sessionPaused, .waitingStarted, .waitingCompleted:
            return .waiting
        case .resourceDetourStarted, .resourceDetourCompleted, .annotationCaptured,
             .extractedEventCreated, .userCorrectionApplied, .scopeChanged:
            return .detour
        case .checkpointStarted, .checkpointCompleted, .checkpointSkipped, .reviewSaved:
            return .checkpoint
        case .interruptionStarted, .interruptionCompleted, .badTimerMarked,
             .sessionAbandoned, .sessionCompleted:
            return .interruption
        case .setupStarted, .setupCompleted, .sideQuestStarted, .sideQuestCompleted,
             .transitionStarted, .transitionCompleted, .intentRecorded, .syncReconciled:
            return .wall
        }
    }

    private func annotationInputMode(for captureMethod: CaptureMethod) -> AnnotationInputMode {
        switch captureMethod {
        case .voice:
            return .voice
        case .quickChip:
            return .quickChip
        case .backgroundSignal:
            return .systemDetected
        case .reviewReconstruction:
            return .reviewNote
        case .manualButton, .lockScreenWidget, .watch, .shortcut, .nfcTag, .calendarImport:
            return .text
        }
    }

    private func updateDurations(at timestamp: Date) {
        guard let startedAt else { return }
        elapsedSeconds = max(0, Int(timestamp.timeIntervalSince(startedAt).rounded()))
        let openActiveSeconds: Int
        if status == .running, openSpan == nil, let activeSegmentStartedAt {
            openActiveSeconds = max(0, Int(timestamp.timeIntervalSince(activeSegmentStartedAt).rounded()))
        } else {
            openActiveSeconds = 0
        }
        let openDetourSeconds: Int
        if openSpan == .resourceDetour, let detourStartedAt {
            openDetourSeconds = max(0, Int(timestamp.timeIntervalSince(detourStartedAt).rounded()))
        } else {
            openDetourSeconds = 0
        }
        detourSeconds = accumulatedDetourSeconds + openDetourSeconds
        activeSeconds = min(elapsedSeconds, accumulatedActiveSeconds + openActiveSeconds)
    }
}
