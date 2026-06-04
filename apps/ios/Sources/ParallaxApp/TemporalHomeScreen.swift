import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

struct TemporalHomeScreen: View {
    @ObservedObject private var timingViewModel: TimingSliceViewModel
    @StateObject private var temporalViewModel: TemporalHomeViewModel
    @Binding private var showsLauncher: Bool
    let initialDrawer: String?
    let startTiming: (MeasurementMode) async -> Void
    @State private var presentedInitialDrawer = false

    init(
        viewModel: TimingSliceViewModel,
        showsLauncher: Binding<Bool>,
        initialDrawer: String?,
        startTiming: @escaping (MeasurementMode) async -> Void
    ) {
        self.timingViewModel = viewModel
        _temporalViewModel = StateObject(wrappedValue: TemporalHomeViewModel(timingViewModel: viewModel))
        _showsLauncher = showsLauncher
        self.initialDrawer = initialDrawer
        self.startTiming = startTiming
    }

    var body: some View {
        CanonicalScreen(
            title: title,
            subtitle: subtitle,
            leadingIcon: "line.3.horizontal",
            leadingAction: {
                temporalViewModel.activeDrawer = .temporalNavigation
            }
        ) {
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
                    startTiming: { mode in
                        await startTiming(mode)
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
        .task(id: ObjectIdentifier(timingViewModel)) {
            temporalViewModel.attachTimingViewModel(timingViewModel)
        }
        .task(id: projectionRefreshKey) {
            temporalViewModel.refreshSurfaceFromTimingProjection()
        }
        .task(id: temporalViewModel.surfaceState) {
            if temporalViewModel.surfaceState == .needsReview {
                await timingViewModel.refreshForgottenTimerEvidence()
            }
        }
        .task {
            await refreshTimerWhileVisible()
        }
    }

    private func refreshTimerWhileVisible() async {
        while !Task.isCancelled {
            timingViewModel.refreshTimer()
            try? await Task.sleep(nanoseconds: 1_000_000_000)
        }
    }

    private var title: String {
        temporalViewModel.surfaceState == .groundedAnswer ? "Ask Time" : "Today"
    }

    private var projectionRefreshKey: String {
        "\(timingViewModel.status.rawValue)-\(timingViewModel.pendingEventCount)-\(timingViewModel.reviewDecision?.rawValue ?? "none")"
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
            let decision = timingViewModel.reviewDecision
                .map { ReviewDecisionDisplayFactory.option(for: $0).title }
                ?? "Decision saved"
            return "Reviewed · \(decision)"
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
            ? pendingChangeCountText
            : "no local changes"
    }

    private var focusProgress: TemporalFocusProgress {
        switch timingViewModel.status {
        case .running:
            let activeShare = CGFloat(timingViewModel.activeSeconds) / CGFloat(max(timingViewModel.elapsedSeconds, 1))
            return TemporalFocusProgress(
                value: min(max(activeShare, 0.08), 1),
                caption: "\(formatDuration(timingViewModel.activeSeconds)) active captured",
                role: .active
            )
        case .paused:
            return TemporalFocusProgress(value: 0.46, caption: "Paused span stays separate", role: .waiting)
        case .completedUnreviewed:
            return TemporalFocusProgress(value: 0.7, caption: "Review before learning updates", role: .checkpoint)
        case .reviewed:
            return TemporalFocusProgress(value: 1, caption: "Reviewed timing evidence saved", role: .detour)
        default:
            return TemporalFocusProgress(value: 0.18, caption: "Start a run to build a range", role: .active)
        }
    }

    private var syncPendingProgress: TemporalFocusProgress {
        let value = timingViewModel.pendingEventCount > 0 ? 0.32 : 0.12
        let caption = timingViewModel.pendingEventCount == 1
            ? "Retry keeps the queue idempotent"
            : "Retry keeps \(timingViewModel.pendingEventCount) changes idempotent"
        return TemporalFocusProgress(value: value, caption: caption, role: .interruption)
    }

    private var pendingChangeCountText: String {
        timingViewModel.pendingEventCount == 1
            ? "1 pending change"
            : "\(timingViewModel.pendingEventCount) pending changes"
    }

    private var pendingSyncSummary: String {
        guard timingViewModel.pendingEventCount > 0 else {
            return "All changes saved"
        }
        return timingViewModel.pendingEventCount == 1
            ? "1 change waiting to sync"
            : "\(timingViewModel.pendingEventCount) changes waiting to sync"
    }

    private var subtitle: String {
        switch temporalViewModel.surfaceState {
        case .defaultHome:
            return "Temporal focus"
        case .needsReview:
            return pendingSyncSummary
        case .syncPending:
            return pendingSyncSummary
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

    @ViewBuilder
    private var defaultHome: some View {
        let canStart = timingViewModel.canStart
        VStack(spacing: 8) {
            temporalFocusCard(
                eyebrow: "CURRENT TIMING FOCUS",
                title: timingViewModel.activityName,
                detail: focusDetail,
                role: .active,
                action: .currentFocusDefault,
                progress: focusProgress
            )
            temporalInsightCard(
                title: "Timing intelligence",
                detail: timingViewModel.detourNote ?? "No reviewed runs yet. Start a run to build a personal range.",
                action: .preflightInsightDefault
            )
            timelineCard(
                title: "Timing signal",
                detail: "Evidence-backed",
                rows: defaultSignalRows,
                density: .compactSignal
            )
            quickCapture(action: .quickCaptureDefault, label: "Capture timing evidence")
            sectionCaption(canStart ? "Need a timing check?" : "Ready to review timing evidence")
            bottomActions(
                left: canStart
                    ? ("Start timer", "begin run", .startTimerDefault)
                    : ("Review run", "approve learning", .reviewRunDefault),
                right: ("Ask time", "grounded answer", .askTimeDefault),
                leftRole: canStart ? .active : .checkpoint,
                rightRole: .detour
            )
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
                .button(
                    timingViewModel.forgottenTimerEvidence.homeRowTitle,
                    timingViewModel.forgottenTimerEvidence.homeRowDetail,
                    .interruption,
                    .eveningCorrectRowNeedsReview
                ),
                .button("Baseline sample", "review before learning", .active, .baselineSampleRowNeedsReview),
                .button("Preflight check", "candidate needs evidence", .detour, .preflightCheckRowNeedsReview),
                .button("Sample support", "ask impact", .wall, .sampleSupportRowNeedsReview),
                .button("Queue ready", "pending changes safe", .waiting, .queueReadyRowNeedsReview),
            ])
            quickCapture(action: .quickCaptureNeedsReview, label: "Add review context")
            bottomActions(
                left: ("Review all", "choose scopes", .reviewAllNeedsReview),
                right: ("Ask impact", "what changes", .askImpactNeedsReview),
                leftRole: .checkpoint,
                rightRole: .detour
            )
        }
    }

    private var syncPendingHome: some View {
        VStack(spacing: 8) {
            temporalFocusCard(
                eyebrow: "SYNC PENDING",
                title: "Backend unavailable",
                detail: "\(pendingSyncSummary) · retry is safe",
                role: .interruption,
                action: .syncFocusSyncPending,
                progress: syncPendingProgress
            )
            temporalInsightCard(
                title: "Local-first sync behavior",
                detail: "Sync order is protected and duplicate retries are ignored.",
                role: .interruption,
                systemName: "arrow.triangle.2.circlepath",
                action: .syncBehaviorSyncPending
            )
            timelineCard(
                title: "Pending evidence",
                detail: "Stored on device",
                rows: syncQueueTimelineRows,
                density: .compactSignal
            )
            quickCapture(action: .quickCaptureSyncPending, label: "Capture while offline")
            sectionCaption("Sync actions")
            bottomActions(
                left: ("Retry sync", "local queue", .retrySyncPending),
                right: ("View queue", "pending events", .viewQueueSyncPending),
                leftRole: .active,
                rightRole: .detour
            )
        }
    }

    private var defaultSignalRows: [TemporalTimelineRowModel] {
        [
            .button(
                timingViewModel.activityName,
                runStatusDetail,
                .active,
                .runningRowDefault,
                lane: "Now",
                badge: timingViewModel.status.displayText
            ),
            .button("Preflight check", "only after real evidence", .detour, .preflightRowDefault, lane: "Prep", badge: "Preflight"),
            .button("Waiting or pause", "wall time stays separate", .waiting, .waitingRowDefault, lane: "Wall", badge: "Waiting"),
            .button("Personal range", "ask when evidence exists", .checkpoint, .baselineRowDefault, lane: "Range", badge: "Baseline"),
            .button("Grounded answer", "evidence-backed only", .wall, .groundedRowDefault, lane: "Ask", badge: "Grounded"),
            .button(
                "Evidence state",
                evidenceDetail,
                .active,
                .evidenceCurrentRowDefault,
                lane: "Sync",
                badge: timingViewModel.pendingEventCount > 0 ? "Queued" : "Current"
            ),
        ]
    }

    private var syncQueueTimelineRows: [TemporalTimelineRowModel] {
        let rows = Array(timingViewModel.pendingSyncRows.prefix(4).enumerated()).map { index, row in
            TemporalTimelineRowModel.button(
                row.title,
                row.detail,
                row.role,
                .viewQueueSyncPending,
                lane: "\(index + 1)",
                badge: "Queued"
            )
        }
        guard !rows.isEmpty else {
            return [
                .display("No local changes", "queue is clear", .active, lane: "Safe", badge: "Clear"),
                .display("Sync order protected", "retry prevents duplicates", .wall, lane: "Seq", badge: "Safe"),
            ]
        }
        return rows + [
            .button("Bearer retry", "backend unavailable", .interruption, .bearerRetryRowSyncPending, lane: "Auth", badge: "Retry"),
            .display("Mutation sequence", "continues safely", .detour, lane: "Seq", badge: "Safe"),
            .display("Stored on device", "raw timing remains local", .waiting, lane: "Local", badge: "Queued"),
        ]
    }

    @ViewBuilder
    private var expandedTimingRun: some View {
        let reviewProjection = timingViewModel.expandedRunReviewProjection
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
                .display(reviewProjection.title, reviewProjection.detail, reviewProjection.role),
            ])
            bottomActions(left: ("Open review", "choose scopes", .openReviewExpandedRun), right: ("Ask similar time", "grounded", .askSimilarTimeExpandedRun))
            wideAction(title: "Start this again", subtitle: "open timing launcher", action: .startAgainExpandedRun)
        }
    }

    @ViewBuilder
    private var groundedAnswer: some View {
        let answer = timingViewModel.lastTemporalQueryAnswer
        let question = temporalViewModel.lastTemporalQuestion
            ?? answer?.question
            ?? "How long does \(timingViewModel.activityName) take?"
        let answerTitle = answer == nil ? "Answer pending evidence" : "Grounded answer"
        let answerDetail = answer?.answerText
            ?? answer?.limitations?.first
            ?? "Parallax will use reviewed runs, sample size, confidence, and limitations."
        let reviewedRunDetail = answer.map { "\($0.sampleSize ?? 0) reviewed sample\(($0.sampleSize ?? 0) == 1 ? "" : "s")" }
            ?? "sample count required"
        let confidenceDetail = answer?.confidence.map { "confidence \($0)" } ?? "computed from runs"
        let sampleCount = answer?.sampleSize ?? 0
        let answerRole: TemporalSemanticRole = sampleCount > 0 ? .active : .waiting
        VStack(spacing: 8) {
            temporalFocusCard(
                eyebrow: "QUESTION",
                title: question,
                detail: answer?.status == nil ? "Submit a grounded timing question." : "Answer status: \(answer?.status ?? "pending")",
                role: .detour,
                action: .questionFocusGroundedAnswer
            )
            temporalAnswerCard(
                title: answerTitle,
                detail: answerDetail,
                sampleDetail: reviewedRunDetail,
                confidenceDetail: confidenceDetail,
                role: answerRole,
                action: .answerSummaryGroundedAnswer
            )
            timelineCard(rows: [
                .button("Reviewed runs", reviewedRunDetail, .active, .reviewedRunsRowGroundedAnswer),
                .button("Resource detours", "from confirmed evidence", .detour, .resourceDetoursRowGroundedAnswer),
                .button("Raw notes shown", "off by default", .privacy, .rawNotesRowGroundedAnswer),
                .button("Median wall time", confidenceDetail, .wall, .medianRowGroundedAnswer),
                .button("Slow-case envelope", "computed from runs", .waiting, .slowCaseRowGroundedAnswer),
                .button("Before starting", "preflight from evidence", .checkpoint, .beforeStartingRowGroundedAnswer),
            ])
            quickCapture(action: .askAnotherGroundedAnswer, label: "Ask another time question")
            bottomActions(
                left: ("Start timer", "begin run", .startTimerGroundedAnswer),
                right: ("Use check", "preflight", .useCheckGroundedAnswer),
                leftRole: .active,
                rightRole: .detour
            )
        }
    }

    private func temporalFocusCard(
        eyebrow: String,
        title: String,
        detail: String,
        role: TemporalSemanticRole,
        action: TemporalHomeAction,
        progress: TemporalFocusProgress? = nil
    ) -> some View {
        Button {
            perform(action)
        } label: {
            Card(background: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)).opacity(role == .interruption ? 0.62 : 0.42)) {
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
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(Color(parallax: .textTertiaryLight))
                }
                if let progress {
                    progressStrip(progress)
                        .padding(.top, 2)
                }
            }
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(title)
        .accessibilityIdentifier(action.rawValue)
    }

    private func temporalInsightCard(
        title: String,
        detail: String,
        role: TemporalSemanticRole = .detour,
        systemName: String = "sparkles",
        action: TemporalHomeAction
    ) -> some View {
        Button {
            perform(action)
        } label: {
            Card {
                HStack(spacing: 11) {
                    CircleIcon(
                        systemName: systemName,
                        tint: Color(parallax: DesignTokenMapper.colorToken(for: role)),
                        fill: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)),
                        size: 42,
                        symbolSize: 16
                    )
                    VStack(alignment: .leading, spacing: 3) {
                        Text(title)
                            .font(.system(size: 13.6, weight: .bold, design: .rounded))
                            .foregroundStyle(Color(parallax: .textPrimaryLight))
                            .lineLimit(1)
                            .minimumScaleFactor(0.72)
                        Text(detail)
                            .font(.system(size: 10.4, weight: .medium, design: .rounded))
                            .foregroundStyle(Color(parallax: .textSecondaryLight))
                            .lineLimit(2)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(Color(parallax: .textTertiaryLight))
                }
            }
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(title)
        .accessibilityIdentifier(action.rawValue)
    }

    private func temporalAnswerCard(
        title: String,
        detail: String,
        sampleDetail: String,
        confidenceDetail: String,
        role: TemporalSemanticRole,
        action: TemporalHomeAction
    ) -> some View {
        Button {
            perform(action)
        } label: {
            Card(background: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)).opacity(0.38)) {
                HStack(alignment: .top, spacing: 11) {
                    CircleIcon(
                        systemName: role == .active ? "checkmark.seal" : "exclamationmark.magnifyingglass",
                        tint: Color(parallax: DesignTokenMapper.colorToken(for: role)),
                        fill: Color(parallax: .cardLight),
                        size: 42,
                        symbolSize: 16
                    )
                    VStack(alignment: .leading, spacing: 4) {
                        Text(title)
                            .font(.system(size: 14.4, weight: .bold, design: .rounded))
                            .foregroundStyle(Color(parallax: .textPrimaryLight))
                            .lineLimit(1)
                            .minimumScaleFactor(0.72)
                        Text(detail)
                            .font(.system(size: 10.8, weight: .medium, design: .rounded))
                            .foregroundStyle(Color(parallax: .textSecondaryLight))
                            .lineLimit(3)
                            .minimumScaleFactor(0.76)
                    }
                    Spacer(minLength: 4)
                    Image(systemName: "chevron.right")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Color(parallax: .textTertiaryLight))
                        .padding(.top, 5)
                }
                HStack(spacing: 6) {
                    answerMetric("Samples", sampleDetail, role: .active)
                    answerMetric("Confidence", confidenceDetail, role: role)
                    answerMetric("Privacy", "raw notes off", role: .privacy)
                }
                .padding(.top, 2)
            }
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(title)
        .accessibilityIdentifier(action.rawValue)
    }

    private func answerMetric(_ title: String, _ detail: String, role: TemporalSemanticRole) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(title)
                .font(.system(size: 8.5, weight: .bold, design: .rounded))
                .foregroundStyle(Color(parallax: DesignTokenMapper.colorToken(for: role)))
                .lineLimit(1)
            Text(detail)
                .font(.system(size: 8.3, weight: .medium, design: .rounded))
                .foregroundStyle(Color(parallax: .textSecondaryLight))
                .lineLimit(1)
                .minimumScaleFactor(0.62)
        }
        .padding(.horizontal, 7)
        .padding(.vertical, 5)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)).opacity(0.78))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private func timelineCard(
        title: String = "Temporal timeline",
        detail: String? = nil,
        rows: [TemporalTimelineRowModel],
        density: TemporalTimelineDensity = .regular
    ) -> some View {
        Card {
            HStack {
                Text(title)
                    .font(.system(size: 12.5, weight: .semibold, design: .rounded))
                Spacer()
                if let detail {
                    Text(detail)
                        .font(.system(size: 8.7, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textTertiaryLight))
                        .lineLimit(1)
                } else {
                    SoftBadge(text: temporalViewModel.surfaceState.displayText, systemName: nil, role: .active)
                }
            }
            ForEach(Array(rows.enumerated()), id: \.offset) { index, row in
                if index > 0 { Divider() }
                rowView(row, density: density)
            }
        }
    }

    @ViewBuilder
    private func rowView(_ row: TemporalTimelineRowModel, density: TemporalTimelineDensity) -> some View {
        switch row.kind {
        case let .button(action):
            Button {
                perform(action)
            } label: {
                rowContent(row, density: density)
            }
            .buttonStyle(.plain)
            .accessibilityElement(children: .combine)
            .accessibilityLabel(row.title)
            .accessibilityIdentifier(action.rawValue)
        case .display:
            rowContent(row, density: density)
        }
    }

    private func rowContent(_ row: TemporalTimelineRowModel, density: TemporalTimelineDensity) -> some View {
        HStack(spacing: density.rowSpacing) {
            if let lane = row.lane {
                Text(lane)
                    .font(.system(size: density.laneFontSize, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textTertiaryLight))
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
                    .frame(width: density.laneWidth, alignment: .trailing)
            }
            CircleIcon(
                systemName: "smallcircle.filled.circle",
                tint: Color(parallax: DesignTokenMapper.colorToken(for: row.role)),
                fill: Color(parallax: DesignTokenMapper.colorToken(for: row.role, soft: true)),
                size: density.iconSize,
                symbolSize: density.symbolSize
            )
            VStack(alignment: .leading, spacing: density.textSpacing) {
                Text(row.title)
                    .font(.system(size: density.titleFontSize, weight: .semibold, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                Text(row.detail)
                    .font(.system(size: density.detailFontSize, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
                    .lineLimit(1)
            }
            Spacer()
            SoftBadge(text: row.badge ?? row.role.displayText, systemName: nil, role: row.role)
            if case .button = row.kind {
                Image(systemName: "chevron.right")
                    .font(.system(size: density.chevronSize, weight: .bold))
                    .foregroundStyle(Color(parallax: .textTertiaryLight))
            }
        }
        .padding(.vertical, density.verticalPadding)
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
    }

    private func progressStrip(_ progress: TemporalFocusProgress) -> some View {
        VStack(spacing: 4) {
            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color(parallax: .separatorLight).opacity(0.65))
                    Capsule()
                        .fill(Color(parallax: DesignTokenMapper.colorToken(for: progress.role)))
                        .frame(width: max(8, proxy.size.width * progress.value))
                }
            }
            .frame(height: 4)
            Text(progress.caption)
                .font(.system(size: 9, weight: .medium, design: .rounded))
                .foregroundStyle(Color(parallax: DesignTokenMapper.colorToken(for: progress.role)))
                .lineLimit(1)
                .minimumScaleFactor(0.72)
                .frame(maxWidth: .infinity, alignment: .center)
        }
    }

    private func sectionCaption(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 10.6, weight: .medium, design: .rounded))
            .foregroundStyle(Color(parallax: .textSecondaryLight))
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.leading, 10)
            .padding(.top, 2)
    }

    private func quickCapture(action: TemporalHomeAction, label: String) -> some View {
        wideAction(title: label, subtitle: "local-first timing note", action: action)
    }

    private func bottomActions(
        left: (String, String, TemporalHomeAction),
        right: (String, String, TemporalHomeAction),
        leftRole: TemporalSemanticRole = .active,
        rightRole: TemporalSemanticRole = .detour
    ) -> some View {
        HStack(spacing: 8) {
            compactAction(title: left.0, subtitle: left.1, action: left.2, role: leftRole)
            compactAction(title: right.0, subtitle: right.1, action: right.2, role: rightRole)
        }
    }

    private func compactAction(title: String, subtitle: String, action: TemporalHomeAction, role: TemporalSemanticRole) -> some View {
        Button {
            perform(action)
        } label: {
            Card(background: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)).opacity(0.62)) {
                HStack(spacing: 8) {
                    CircleIcon(systemName: "arrow.up.right", tint: Color(parallax: DesignTokenMapper.colorToken(for: role)), fill: Color(parallax: .cardLight), size: 30, symbolSize: 12)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(title)
                            .font(.system(size: 12.2, weight: .bold, design: .rounded))
                            .lineLimit(1)
                            .minimumScaleFactor(0.65)
                        Text(subtitle)
                            .font(.system(size: 10.2, weight: .medium, design: .rounded))
                            .foregroundStyle(Color(parallax: .textSecondaryLight))
                            .lineLimit(1)
                            .minimumScaleFactor(0.65)
                    }
                }
            }
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Color(parallax: DesignTokenMapper.colorToken(for: role)).opacity(0.18), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(title)
        .accessibilityIdentifier(action.rawValue)
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
                        .font(.system(size: 22, weight: .medium))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                }
            }
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(title)
        .accessibilityIdentifier(action.rawValue)
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
            TemporalNavigationDrawerView { destination in
                temporalViewModel.performTemporalNavigation(destination)
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case .askTime:
            AskTimeDrawerView(activityName: timingViewModel.activityName) { question in
                Task { await temporalViewModel.submitTemporalQuestion(question) }
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
            SyncQueueDrawerView(rows: timingViewModel.pendingSyncRows, pendingCount: timingViewModel.pendingEventCount) {
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
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case .temporalAnswerEvidence:
            TemporalAnswerEvidenceDrawerView {
                Task {
                    await timingViewModel.refreshPreflightEvidence()
                    temporalViewModel.activeDrawer = .phase8(.preflightEvidence)
                }
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
            StepDetailDrawerView(detail: timingViewModel.stepDetail) { action in
                Task { await temporalViewModel.performDrawerAction(action) }
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case .frictionEvidence:
            FrictionEvidenceDrawerView(evidence: timingViewModel.frictionEvidence) { action in
                Task { await temporalViewModel.performDrawerAction(action) }
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case .forgottenTimer:
            ForgottenTimerDrawerView(evidence: timingViewModel.forgottenTimerEvidence) { action in
                Task { await temporalViewModel.performDrawerAction(action) }
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case .reviewDecision:
            ReviewDecisionDrawerView(selectedDecision: timingViewModel.reviewDecision ?? .saveUsefulRun) { decision in
                Task {
                    await timingViewModel.saveReviewDecision(decision)
                    temporalViewModel.dismissDrawer()
                }
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case .preflightEvidence:
            PreflightEvidenceDrawerView(evidence: timingViewModel.preflightEvidence) { action in
                Task { await temporalViewModel.performDrawerAction(action) }
            } dismiss: {
                temporalViewModel.dismissDrawer()
            }
        case .checkpointSetup:
            CheckpointSetupDrawerView { action in
                Task { await temporalViewModel.performDrawerAction(action) }
            } dismiss: {
                temporalViewModel.dismissDrawer()
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
    let lane: String?
    let badge: String?

    static func button(
        _ title: String,
        _ detail: String,
        _ role: TemporalSemanticRole,
        _ action: TemporalHomeAction,
        lane: String? = nil,
        badge: String? = nil
    ) -> TemporalTimelineRowModel {
        TemporalTimelineRowModel(title: title, detail: detail, role: role, kind: .button(action), lane: lane, badge: badge)
    }

    static func display(
        _ title: String,
        _ detail: String,
        _ role: TemporalSemanticRole,
        lane: String? = nil,
        badge: String? = nil
    ) -> TemporalTimelineRowModel {
        TemporalTimelineRowModel(title: title, detail: detail, role: role, kind: .display, lane: lane, badge: badge)
    }
}

private struct TemporalFocusProgress {
    let value: CGFloat
    let caption: String
    let role: TemporalSemanticRole
}

private enum TemporalTimelineDensity {
    case regular
    case compactSignal

    var rowSpacing: CGFloat {
        switch self {
        case .regular: 8
        case .compactSignal: 6
        }
    }

    var laneWidth: CGFloat {
        switch self {
        case .regular: 0
        case .compactSignal: 29
        }
    }

    var laneFontSize: CGFloat {
        switch self {
        case .regular: 0
        case .compactSignal: 8.8
        }
    }

    var iconSize: CGFloat {
        switch self {
        case .regular: 28
        case .compactSignal: 24
        }
    }

    var symbolSize: CGFloat {
        switch self {
        case .regular: 11
        case .compactSignal: 9
        }
    }

    var titleFontSize: CGFloat {
        switch self {
        case .regular: 12
        case .compactSignal: 10.9
        }
    }

    var detailFontSize: CGFloat {
        switch self {
        case .regular: 10
        case .compactSignal: 8.8
        }
    }

    var textSpacing: CGFloat {
        switch self {
        case .regular: 2
        case .compactSignal: 1
        }
    }

    var verticalPadding: CGFloat {
        switch self {
        case .regular: 2
        case .compactSignal: 0
        }
    }

    var chevronSize: CGFloat {
        switch self {
        case .regular: 12
        case .compactSignal: 10
        }
    }
}
