import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

struct TemporalHomeScreen: View {
    @ObservedObject private var timingViewModel: TimingSliceViewModel
    @StateObject private var temporalViewModel: TemporalHomeViewModel
    @Binding private var showsLauncher: Bool
    let initialDrawer: String?
    let startTiming: () async -> Void
    @State private var presentedInitialDrawer = false

    init(
        viewModel: TimingSliceViewModel,
        showsLauncher: Binding<Bool>,
        initialDrawer: String?,
        startTiming: @escaping () async -> Void
    ) {
        self.timingViewModel = viewModel
        _temporalViewModel = StateObject(wrappedValue: TemporalHomeViewModel(timingViewModel: viewModel))
        _showsLauncher = showsLauncher
        self.initialDrawer = initialDrawer
        self.startTiming = startTiming
    }

    var body: some View {
        CanonicalScreen(title: title, subtitle: subtitle, leadingIcon: "line.3.horizontal") {
            switch temporalViewModel.surfaceState {
            case .defaultHome:
                defaultHome
            case .needsReview:
                needsReviewHome
            case .syncPending:
                syncPendingHome
            case .expandedTimingRun:
                expandedTimingRun
            case .groundedAnswer:
                groundedAnswer
            }
        }
        .overlay(alignment: .bottom) {
            if showsLauncher || temporalViewModel.showsLauncher {
                TimingLauncherSheet(
                    activityName: timingViewModel.activityName,
                    startTiming: {
                        await startTiming()
                        temporalViewModel.dismissLauncher()
                    },
                    dismiss: {
                        showsLauncher = false
                        temporalViewModel.dismissLauncher()
                    }
                )
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .overlay {
            if let drawer = temporalViewModel.activeDrawer {
                drawerOverlay(drawer)
            }
        }
        .task {
            guard !presentedInitialDrawer else { return }
            presentedInitialDrawer = true
            if let initialDrawer, let drawer = Phase8DrawerWorkflow(rawDemoValue: initialDrawer) {
                temporalViewModel.activeDrawer = .phase8(drawer)
            }
        }
    }

    private var title: String {
        temporalViewModel.surfaceState == .groundedAnswer ? "Ask Time" : "Today"
    }

    private var focusDetail: String {
        switch timingViewModel.status {
        case .running:
            return "Running \(formatDuration(timingViewModel.elapsedSeconds)) · active \(formatDuration(timingViewModel.activeSeconds))"
        case .paused:
            return "Paused · \(formatDuration(timingViewModel.elapsedSeconds)) elapsed"
        case .completedUnreviewed:
            return "Finished · review decides what this teaches"
        case .reviewed:
            return "Reviewed · \(timingViewModel.reviewDecision?.rawValue ?? "decision saved")"
        default:
            return "Ready to time this activity"
        }
    }

    private var runStatusDetail: String {
        timingViewModel.status == .running
            ? "\(formatDuration(timingViewModel.elapsedSeconds)) elapsed"
            : "open launcher"
    }

    private var evidenceDetail: String {
        timingViewModel.pendingEventCount > 0
            ? "\(timingViewModel.pendingEventCount) local mutation\(timingViewModel.pendingEventCount == 1 ? "" : "s")"
            : "no local queue"
    }

    private var subtitle: String {
        switch temporalViewModel.surfaceState {
        case .defaultHome:
            return "Temporal focus"
        case .needsReview:
            return "\(timingViewModel.pendingEventCount) local mutation\(timingViewModel.pendingEventCount == 1 ? "" : "s") pending"
        case .syncPending:
            return "4 local mutations pending"
        case .expandedTimingRun:
            return "Timing run evidence"
        case .groundedAnswer:
            return "Grounded temporal answer"
        }
    }

    private func formatDuration(_ seconds: Int) -> String {
        let minutes = seconds / 60
        let remainder = seconds % 60
        return "\(minutes):\(String(format: "%02d", remainder))"
    }

    private var defaultHome: some View {
        VStack(spacing: 8) {
            temporalFocusCard(
                eyebrow: "CURRENT TIMING FOCUS",
                title: timingViewModel.activityName,
                detail: focusDetail,
                role: .active,
                action: .currentFocusDefault
            )
            temporalInsightCard(
                title: "Timing intelligence",
                detail: timingViewModel.detourNote ?? "No reviewed runs yet. Start a run to build a personal range.",
                action: .preflightInsightDefault
            )
            timelineCard(rows: [
                .button(timingViewModel.activityName, runStatusDetail, .active, .runningRowDefault),
                .button("Preflight check", "only after real evidence", .detour, .preflightRowDefault),
                .button("Waiting or pause", "wall time stays separate", .waiting, .waitingRowDefault),
                .button("Personal range", "ask when evidence exists", .checkpoint, .baselineRowDefault),
                .button("Grounded answer", "evidence-backed only", .wall, .groundedRowDefault),
                .button("Evidence state", evidenceDetail, .active, .evidenceCurrentRowDefault),
            ])
            quickCapture(action: .quickCaptureDefault, label: "Capture timing evidence")
            bottomActions(left: ("Review run", "approve learning", .reviewRunDefault), right: ("Ask time", "grounded answer", .askTimeDefault))
        }
    }

    private var needsReviewHome: some View {
        VStack(spacing: 8) {
            temporalFocusCard(
                eyebrow: "NEEDS REVIEW",
                title: "Run needs review",
                detail: "Choose what updates timing baselines and friction checks.",
                role: .checkpoint,
                action: .reviewFocusNeedsReview
            )
            temporalInsightCard(
                title: "Learning impact pending",
                detail: "Approving runs can update wall range and preflight checks.",
                action: .learningImpactNeedsReview
            )
            timelineCard(rows: [
                .button("Run review", "choose scopes", .checkpoint, .runReviewRowNeedsReview),
                .button("Evening reset correct", "possible forgotten timer", .interruption, .eveningCorrectRowNeedsReview),
                .button("Baseline sample", "review before learning", .active, .baselineSampleRowNeedsReview),
                .button("Preflight check", "candidate needs evidence", .detour, .preflightCheckRowNeedsReview),
                .button("Sample support", "ask impact", .wall, .sampleSupportRowNeedsReview),
                .button("Queue ready", "local mutations safe", .waiting, .queueReadyRowNeedsReview),
            ])
            quickCapture(action: .quickCaptureNeedsReview, label: "Add review context")
            bottomActions(left: ("Review all", "choose scopes", .reviewAllNeedsReview), right: ("Ask impact", "what changes", .askImpactNeedsReview))
        }
    }

    private var syncPendingHome: some View {
        VStack(spacing: 8) {
            temporalFocusCard(
                eyebrow: "SYNC PENDING",
                title: "Backend unavailable",
                detail: "\(timingViewModel.pendingEventCount) local mutations pending · retry is safe",
                role: .waiting,
                action: .syncFocusSyncPending
            )
            temporalInsightCard(
                title: "Local-first sync behavior",
                detail: "Mutation order and idempotency keys are preserved.",
                action: .syncBehaviorSyncPending
            )
            timelineCard(rows: [
                .button("session_started queued", "sequence 1", .active, .sessionStartedRowSyncPending),
                .button("resource_detour queued", "sequence 2", .detour, .resourceDetourRowSyncPending),
                .button("review_saved queued", "sequence 3", .checkpoint, .reviewSavedRowSyncPending),
                .button("preflight decision queued", "sequence 4", .waiting, .preflightDecisionRowSyncPending),
                .button("Bearer retry", "retry", .interruption, .bearerRetryRowSyncPending),
                .display("Mutation sequence safe", "idempotency preserved", .wall),
            ])
            quickCapture(action: .quickCaptureSyncPending, label: "Capture while offline")
            bottomActions(left: ("Retry sync", "local queue", .retrySyncPending), right: ("View queue", "pending events", .viewQueueSyncPending))
        }
    }

    private var expandedTimingRun: some View {
        VStack(spacing: 8) {
            temporalFocusCard(
                eyebrow: "TIMING RUN EVIDENCE",
                title: timingViewModel.activityName,
                detail: "\(formatDuration(timingViewModel.elapsedSeconds)) wall · \(formatDuration(timingViewModel.activeSeconds)) active",
                role: .active,
                action: .currentFocusDefault
            )
            timelineCard(rows: [
                .display("Started", "manual timer", .active),
                .display("Friction", timingViewModel.detourNote ?? "none captured", .detour),
                .display("Checkpoint", timingViewModel.currentCheckpointLabel, .checkpoint),
                .display("Review ready", "model inclusion pending", .waiting),
            ])
            bottomActions(left: ("Open review", "choose scopes", .openReviewExpandedRun), right: ("Ask similar time", "grounded", .askSimilarTimeExpandedRun))
            wideAction(title: "Start this again", subtitle: "open timing launcher", action: .startAgainExpandedRun)
        }
    }

    private var groundedAnswer: some View {
        VStack(spacing: 8) {
            temporalFocusCard(
                eyebrow: "QUESTION",
                title: "How long does \(timingViewModel.activityName) take?",
                detail: "Answered from reviewed runs and confirmed detours.",
                role: .detour,
                action: .questionFocusGroundedAnswer
            )
            temporalInsightCard(
                title: "Answer pending evidence",
                detail: "Parallax will use reviewed runs, sample size, confidence, and limitations.",
                action: .answerSummaryGroundedAnswer
            )
            timelineCard(rows: [
                .button("Reviewed runs", "sample count required", .active, .reviewedRunsRowGroundedAnswer),
                .button("Resource detours", "from confirmed evidence", .detour, .resourceDetoursRowGroundedAnswer),
                .button("Raw notes shown", "off by default", .privacy, .rawNotesRowGroundedAnswer),
                .button("Median wall time", "computed from runs", .wall, .medianRowGroundedAnswer),
                .button("Slow-case envelope", "computed from runs", .waiting, .slowCaseRowGroundedAnswer),
                .button("Before starting", "preflight from evidence", .checkpoint, .beforeStartingRowGroundedAnswer),
            ])
            quickCapture(action: .askAnotherGroundedAnswer, label: "Ask another time question")
            bottomActions(left: ("Start timer", "begin run", .startTimerGroundedAnswer), right: ("Use check", "preflight", .useCheckGroundedAnswer))
        }
    }

    private func temporalFocusCard(eyebrow: String, title: String, detail: String, role: TemporalSemanticRole, action: TemporalHomeAction) -> some View {
        Button {
            perform(action)
        } label: {
            Card(background: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)).opacity(0.42)) {
                Text(eyebrow)
                    .font(.system(size: 9, weight: .bold, design: .rounded))
                    .tracking(1.4)
                    .foregroundStyle(Color(parallax: DesignTokenMapper.colorToken(for: role)))
                HStack(spacing: 10) {
                    CircleIcon(systemName: "timer", tint: Color(parallax: DesignTokenMapper.colorToken(for: role)), fill: Color(parallax: .cardLight), size: 48, symbolSize: 18)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(title)
                            .font(.system(size: 17, weight: .bold, design: .rounded))
                            .foregroundStyle(Color(parallax: .textPrimaryLight))
                            .lineLimit(2)
                            .minimumScaleFactor(0.7)
                        Text(detail)
                            .font(.system(size: 11, weight: .medium, design: .rounded))
                            .foregroundStyle(Color(parallax: .textSecondaryLight))
                            .lineLimit(2)
                            .minimumScaleFactor(0.72)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundStyle(Color(parallax: .textTertiaryLight))
                }
            }
        }
        .buttonStyle(.plain)
    }

    private func temporalInsightCard(title: String, detail: String, action: TemporalHomeAction) -> some View {
        Button {
            perform(action)
        } label: {
            Card {
                HStack(spacing: 10) {
                    CircleIcon(systemName: "sparkles", tint: Color(parallax: .detourText), fill: Color(parallax: .detourSoft), size: 38, symbolSize: 15)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(title)
                            .font(.system(size: 13, weight: .bold, design: .rounded))
                            .foregroundStyle(Color(parallax: .textPrimaryLight))
                            .lineLimit(1)
                            .minimumScaleFactor(0.72)
                        Text(detail)
                            .font(.system(size: 10.5, weight: .medium, design: .rounded))
                            .foregroundStyle(Color(parallax: .textSecondaryLight))
                            .lineLimit(2)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(Color(parallax: .textTertiaryLight))
                }
            }
        }
        .buttonStyle(.plain)
    }

    private func timelineCard(rows: [TemporalTimelineRowModel]) -> some View {
        Card {
            HStack {
                Text("Temporal timeline")
                    .font(.system(size: 12.5, weight: .semibold, design: .rounded))
                Spacer()
                SoftBadge(text: temporalViewModel.surfaceState.rawValue, systemName: nil, role: .active)
            }
            ForEach(Array(rows.enumerated()), id: \.offset) { index, row in
                if index > 0 { Divider() }
                rowView(row)
            }
        }
    }

    @ViewBuilder
    private func rowView(_ row: TemporalTimelineRowModel) -> some View {
        switch row.kind {
        case let .button(action):
            Button {
                perform(action)
            } label: {
                rowContent(row)
            }
            .buttonStyle(.plain)
        case .display:
            rowContent(row)
        }
    }

    private func rowContent(_ row: TemporalTimelineRowModel) -> some View {
        HStack(spacing: 8) {
            CircleIcon(
                systemName: "smallcircle.filled.circle",
                tint: Color(parallax: DesignTokenMapper.colorToken(for: row.role)),
                fill: Color(parallax: DesignTokenMapper.colorToken(for: row.role, soft: true)),
                size: 28,
                symbolSize: 11
            )
            VStack(alignment: .leading, spacing: 2) {
                Text(row.title)
                    .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                Text(row.detail)
                    .font(.system(size: 9.5, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
                    .lineLimit(1)
            }
            Spacer()
            SoftBadge(text: row.role.rawValue, systemName: nil, role: row.role)
            if case .button = row.kind {
                Image(systemName: "chevron.right")
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(Color(parallax: .textTertiaryLight))
            }
        }
        .padding(.vertical, 2)
    }

    private func quickCapture(action: TemporalHomeAction, label: String) -> some View {
        wideAction(title: label, subtitle: "local-first timing note", action: action)
    }

    private func bottomActions(
        left: (String, String, TemporalHomeAction),
        right: (String, String, TemporalHomeAction)
    ) -> some View {
        HStack(spacing: 8) {
            compactAction(title: left.0, subtitle: left.1, action: left.2, role: .checkpoint)
            compactAction(title: right.0, subtitle: right.1, action: right.2, role: .detour)
        }
    }

    private func compactAction(title: String, subtitle: String, action: TemporalHomeAction, role: TemporalSemanticRole) -> some View {
        Button {
            perform(action)
        } label: {
            Card {
                HStack(spacing: 8) {
                    CircleIcon(systemName: "arrow.up.right", tint: Color(parallax: DesignTokenMapper.colorToken(for: role)), fill: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)), size: 30, symbolSize: 12)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(title)
                            .font(.system(size: 11, weight: .bold, design: .rounded))
                            .lineLimit(1)
                            .minimumScaleFactor(0.65)
                        Text(subtitle)
                            .font(.system(size: 9, weight: .medium, design: .rounded))
                            .foregroundStyle(Color(parallax: .textSecondaryLight))
                            .lineLimit(1)
                            .minimumScaleFactor(0.65)
                    }
                }
            }
        }
        .buttonStyle(.plain)
    }

    private func wideAction(title: String, subtitle: String, action: TemporalHomeAction) -> some View {
        Button {
            perform(action)
        } label: {
            Card {
                HStack(spacing: 10) {
                    CircleIcon(systemName: "plus", tint: .white, fill: Color(parallax: .active), size: 36, symbolSize: 15)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(title)
                            .font(.system(size: 12.5, weight: .semibold, design: .rounded))
                        Text(subtitle)
                            .font(.system(size: 10, weight: .medium, design: .rounded))
                            .foregroundStyle(Color(parallax: .textSecondaryLight))
                    }
                    Spacer()
                    Image(systemName: "mic")
                        .font(.title3)
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                }
            }
        }
        .buttonStyle(.plain)
    }

    private func perform(_ action: TemporalHomeAction) {
        Task {
            await temporalViewModel.perform(action)
            if temporalViewModel.showsLauncher {
                showsLauncher = true
            }
        }
    }

    @ViewBuilder
    private func drawerOverlay(_ drawer: TemporalHomeDrawerKind) -> some View {
        switch drawer {
        case .temporalNavigation:
            TemporalNavigationDrawerView { surface in
                temporalViewModel.setSurface(surface)
                temporalViewModel.dismissDrawer()
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case .quickCapture:
            QuickCaptureDrawerView { note in
                Task { await temporalViewModel.saveQuickCapture(note) }
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case .syncQueue:
            SyncQueueDrawerView(pendingCount: timingViewModel.pendingEventCount) {
                Task { await temporalViewModel.retrySync() }
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case .timingRunEvidence:
            TimingRunEvidenceDrawerView {
                temporalViewModel.activeDrawer = .phase8(.reviewDecision)
            } askSimilarTime: {
                perform(.askSimilarTimeExpandedRun)
            } startAgain: {
                perform(.startAgainExpandedRun)
            }
        case .temporalAnswerEvidence:
            TemporalAnswerEvidenceDrawerView {
                temporalViewModel.activeDrawer = .phase8(.preflightEvidence)
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case let .phase8(workflow):
            phase8Drawer(workflow)
        }
    }

    @ViewBuilder
    private func phase8Drawer(_ workflow: Phase8DrawerWorkflow) -> some View {
        switch workflow {
        case .stepDetail:
            StepDetailDrawerView { action in
                Task { await temporalViewModel.performDrawerAction(action) }
            }
        case .frictionEvidence:
            FrictionEvidenceDrawerView { action in
                Task { await temporalViewModel.performDrawerAction(action) }
            }
        case .forgottenTimer:
            ForgottenTimerDrawerView { action in
                Task { await temporalViewModel.performDrawerAction(action) }
            }
        case .reviewDecision:
            ReviewDecisionDrawerView(selectedDecision: timingViewModel.reviewDecision ?? .saveUsefulRun) { decision in
                Task {
                    await timingViewModel.saveReviewDecision(decision)
                    temporalViewModel.dismissDrawer()
                }
            }
        case .preflightEvidence:
            PreflightEvidenceDrawerView { action in
                Task { await temporalViewModel.performDrawerAction(action) }
            }
        case .checkpointSetup:
            CheckpointSetupDrawerView { action in
                Task { await temporalViewModel.performDrawerAction(action) }
            }
        }
    }
}

private struct TemporalTimelineRowModel {
    enum Kind {
        case button(TemporalHomeAction)
        case display
    }

    let title: String
    let detail: String
    let role: TemporalSemanticRole
    let kind: Kind

    static func button(_ title: String, _ detail: String, _ role: TemporalSemanticRole, _ action: TemporalHomeAction) -> TemporalTimelineRowModel {
        TemporalTimelineRowModel(title: title, detail: detail, role: role, kind: .button(action))
    }

    static func display(_ title: String, _ detail: String, _ role: TemporalSemanticRole) -> TemporalTimelineRowModel {
        TemporalTimelineRowModel(title: title, detail: detail, role: role, kind: .display)
    }
}
