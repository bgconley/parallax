import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

public enum TimingInstrumentLayout {
    public static let instrumentCardPadding: CGFloat = 14
    public static let instrumentSectionSpacing: CGFloat = 12
    public static let instrumentOverviewHeight: CGFloat = 124
    public static let primaryButtonHeight: CGFloat = 50
    public static let secondaryButtonHeight: CGFloat = 46
    public static let badgeFontSize: CGFloat = 10.4
    public static let badgeMinHeight: CGFloat = 24
    public static let badgeRowSpacing: CGFloat = 8
    public static let badgeRailVerticalSpacing: CGFloat = 7
    public static let secondaryButtonUsesSystemBorderedStyle = true
    public static let secondaryButtonUsesCompactVerticalLabel = true
    public static let bottomDockIsAnchoredToSafeArea = true
    public static let bottomDockReservesScrollContentSpace = true
    public static let bottomDockUsesSheetShape = true
    public static let bottomDockUsesOverlayAttachment = true
    public static let bottomDockExtendsThroughBottomSafeArea = true
    public static let bottomDockSafeAreaFillMinimum: CGFloat = 18
    public static let bottomDockScrollReservation: CGFloat = 148
    public static let stepPreviewDoesNotDuplicateMainNoteAction = true
    public static let bottomDockRepeatsPrimaryActions = false

    public static func bottomDockSafeAreaExtension(for safeAreaBottom: CGFloat) -> CGFloat {
        max(safeAreaBottom, bottomDockSafeAreaFillMinimum)
    }

    public static func bottomDockAttachmentOffset(for safeAreaBottom: CGFloat) -> CGFloat {
        bottomDockSafeAreaExtension(for: safeAreaBottom)
    }

    public static func bottomDockBottomPadding(for safeAreaBottom: CGFloat) -> CGFloat {
        ParallaxBottomSheetLayout.bottomContentPadding
            + bottomDockSafeAreaExtension(for: safeAreaBottom) * 2
    }

    public static func ringSize(for cardWidth: CGFloat) -> CGFloat {
        min(max(cardWidth * 0.32, 108), 124)
    }

    public static func infoLaneSpacing(for cardWidth: CGFloat) -> CGFloat {
        min(max(cardWidth * 0.075, 24), 34)
    }

    public static func infoLaneWidth(for cardWidth: CGFloat) -> CGFloat {
        max(0, cardWidth - ringSize(for: cardWidth) - infoLaneSpacing(for: cardWidth))
    }
}

struct TimingSessionScreen: View {
    @ObservedObject var viewModel: TimingSliceViewModel
    let initialDrawer: String?
    let finishAndReview: () async -> Void
    let goBack: () -> Void
    @State private var activeDrawer: Phase8DrawerWorkflow?
    @State private var showsFrictionCapture = false
    @State private var showsStepNoteCapture = false
    @State private var presentedInitialDrawer = false

    var body: some View {
        GeometryReader { proxy in
            ZStack(alignment: .bottom) {
                CanonicalScreen(
                    title: "Timing Session",
                    subtitle: "Observing how this run really goes\nQuick taps are enough — I’ll learn from the evidence.",
                    leadingIcon: "chevron.left",
                    leadingAction: goBack
                ) {
                    ActivitySummaryRow(
                        title: viewModel.activityName,
                        subtitle: "No reviewed range yet",
                        detail: "Basis: your reviewed timing runs",
                        icon: "sparkles"
                    )
                    badgeRail
                    instrumentCard
                    stepPreviewCard
                    Color.clear
                        .frame(height: TimingInstrumentLayout.bottomDockScrollReservation)
                }
                bottomActionDock(safeAreaBottom: proxy.safeAreaInsets.bottom)
                    .ignoresSafeArea(.container, edges: .bottom)
            }
            .background(Color(parallax: .canvasLight).ignoresSafeArea())
        }
        .overlay {
            if let activeDrawer {
                sessionDrawerOverlay(activeDrawer)
            }
            if showsFrictionCapture {
                FrictionCaptureDrawerView(
                    activityName: viewModel.activityName,
                    existingNote: viewModel.detourNote,
                    dismiss: { showsFrictionCapture = false },
                    save: { resourceName, note in
                        Task {
                            await viewModel.logFriction(resourceName: resourceName, note: note)
                            showsFrictionCapture = false
                        }
                    }
                )
            }
            if showsStepNoteCapture {
                QuickCaptureDrawerView { note in
                    Task {
                        await viewModel.captureStepNote(note)
                        showsStepNoteCapture = false
                    }
                } dismiss: {
                    showsStepNoteCapture = false
                }
            }
        }
        .task {
            guard !presentedInitialDrawer else { return }
            presentedInitialDrawer = true
            if let initialDrawer, let drawer = Phase8DrawerWorkflow(rawDemoValue: initialDrawer),
               drawer == .stepDetail || drawer == .frictionEvidence {
                activeDrawer = drawer
            }
        }
        .task {
            await refreshTimerWhileVisible()
        }
    }

    private func refreshTimerWhileVisible() async {
        while !Task.isCancelled {
            viewModel.refreshTimer()
            try? await Task.sleep(nanoseconds: 1_000_000_000)
        }
    }

    private var badgeRail: some View {
        VStack(spacing: TimingInstrumentLayout.badgeRailVerticalSpacing) {
            HStack(spacing: TimingInstrumentLayout.badgeRowSpacing) {
                Spacer(minLength: 0)
                TimingRailBadge(text: modeBadgeTitle, systemName: "checkmark.circle", role: .active)
                TimingRailBadge(text: "Personal model", systemName: "leaf", role: .detour)
                Spacer(minLength: 0)
            }
            HStack(spacing: TimingInstrumentLayout.badgeRowSpacing) {
                Spacer(minLength: 0)
                TimingRailBadge(text: "Active + elapsed", systemName: "waveform.path.ecg", role: .checkpoint)
                TimingRailBadge(text: "Low burden", systemName: "heart", role: .checkpoint)
                Spacer(minLength: 0)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 2)
    }

    private var modeBadgeTitle: String {
        switch viewModel.measurementMode {
        case .wholeTask:
            return "Whole-task timing"
        case .checkpointed:
            return "Checkpointed timing"
        case .routine:
            return "Repeated timing"
        case .calibration:
            return "Calibration timing"
        case .estimateOnly:
            return "Estimate-only timing"
        case .passive:
            return "Passive timing"
        }
    }

    private var currentWorkTitle: String {
        viewModel.isCheckpointedMode ? viewModel.currentCheckpointLabel : "Whole activity"
    }

    private var currentWorkSubtitle: String {
        viewModel.isCheckpointedMode
            ? "Checkpoint labels are optional"
            : "One timer for this run"
    }

    private func formatTimer(_ seconds: Int) -> String {
        let minutes = seconds / 60
        let remainder = seconds % 60
        return "\(minutes):\(String(format: "%02d", remainder))"
    }

    private var activeShareLabel: String {
        guard viewModel.elapsedSeconds > 0 else { return "0% active" }
        let ratio = Double(viewModel.activeSeconds) / Double(max(viewModel.elapsedSeconds, 1))
        return "\(Int((min(max(ratio, 0), 1) * 100).rounded()))% active"
    }

    private var pendingChangeLabel: String {
        guard viewModel.pendingEventCount > 0 else {
            return "All changes saved"
        }
        return viewModel.pendingEventCount == 1
            ? "1 change waiting to sync"
            : "\(viewModel.pendingEventCount) changes waiting to sync"
    }

    private var frictionLabel: String {
        viewModel.detourNote.map { "Friction: \($0)" } ?? "No friction noted"
    }

    private var instrumentCard: some View {
        VStack(alignment: .leading, spacing: TimingInstrumentLayout.instrumentSectionSpacing) {
            GeometryReader { proxy in
                let ringSize = TimingInstrumentLayout.ringSize(for: proxy.size.width)
                let infoSpacing = TimingInstrumentLayout.infoLaneSpacing(for: proxy.size.width)
                let infoWidth = TimingInstrumentLayout.infoLaneWidth(for: proxy.size.width)
                HStack(alignment: .center, spacing: infoSpacing) {
                    TimingRing(elapsedSeconds: viewModel.elapsedSeconds, activeSeconds: viewModel.activeSeconds)
                        .frame(width: ringSize, height: ringSize)
                        .layoutPriority(0)
                    VStack(alignment: .leading, spacing: 4) {
                        SoftBadge(text: viewModel.status.displayText, systemName: nil, role: .active)
                        Text(currentWorkTitle)
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            .lineLimit(2)
                            .minimumScaleFactor(0.72)
                        Text(currentWorkSubtitle)
                            .font(.system(size: 10.5, weight: .medium, design: .rounded))
                            .foregroundStyle(Color(parallax: .textSecondaryLight))
                        CompactLabel(activeShareLabel, systemName: "chart.pie")
                        CompactLabel(pendingChangeLabel, systemName: viewModel.pendingEventCount == 0 ? "checkmark.circle" : "arrow.triangle.2.circlepath")
                        CompactLabel(frictionLabel, systemName: "exclamationmark.bubble")
                    }
                    .frame(minWidth: infoWidth, maxWidth: .infinity, alignment: .leading)
                    .layoutPriority(1)
                }
            }
            .frame(height: TimingInstrumentLayout.instrumentOverviewHeight)
            SessionPrimaryStepButton(title: viewModel.isCheckpointedMode ? "Complete checkpoint" : "Finish + review") {
                Task {
                    if viewModel.isCheckpointedMode {
                        await viewModel.completeCurrentCheckpoint()
                    } else {
                        await finishAndReview()
                    }
                }
            }
            HStack(spacing: 9) {
                SessionAction(title: viewModel.status == .paused ? "Resume" : "Pause", icon: "pause.circle") {
                    Task {
                        if viewModel.status == .paused {
                            await viewModel.resumeRun()
                        } else {
                            await viewModel.pauseCurrentStep()
                        }
                    }
                }
                SessionAction(title: "Friction", icon: "bubble.left") {
                    showsFrictionCapture = true
                }
                if viewModel.isCheckpointedMode {
                    SessionAction(title: "Skip", icon: "forward") {
                        Task { await viewModel.skipCurrentCheckpoint() }
                    }
                    SessionAction(title: "Move", icon: "arrow.up.arrow.down") {
                        Task { await viewModel.moveCurrentCheckpoint() }
                    }
                } else {
                    SessionAction(title: "Note", icon: "square.and.pencil") {
                        showsStepNoteCapture = true
                    }
                    SessionAction(title: "More", icon: "ellipsis") {
                        activeDrawer = viewModel.detourNote == nil ? nil : .frictionEvidence
                        if activeDrawer == nil {
                            showsStepNoteCapture = true
                        }
                    }
                }
            }
        }
        .padding(TimingInstrumentLayout.instrumentCardPadding)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(parallax: .cardLight))
        .overlay(
            RoundedRectangle(cornerRadius: 18)
                .stroke(Color(parallax: .separatorLight), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .shadow(color: .black.opacity(0.045), radius: 9, y: 3)
    }

    @ViewBuilder
    private var stepPreviewCard: some View {
        if viewModel.isCheckpointedMode {
            Card {
                StepRow(index: 1, title: "Start timer", estimate: "timed now", tag: "source event", status: .done, trailingText: "started")
                Divider()
                StepRow(index: 2, title: viewModel.currentCheckpointLabel, estimate: "active now", tag: "current", status: .running, trailingText: formatTimer(viewModel.activeSeconds))
                Divider()
                StepRow(index: 3, title: viewModel.nextCheckpointLabel, estimate: "optional", tag: "pending", status: .pending)
                Button {
                    activeDrawer = .stepDetail
                } label: {
                    Label("Show checkpoints", systemImage: "list.bullet")
                        .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                        .frame(maxWidth: .infinity, minHeight: 30)
                }
                .buttonStyle(.bordered)
            }
        } else {
            Card {
                StepRow(index: 1, title: "Start timer", estimate: "timed now", tag: "source event", status: .done, trailingText: "started")
                Divider()
                StepRow(index: 2, title: viewModel.activityName, estimate: "active run", tag: viewModel.status.displayText, status: .running, trailingText: formatTimer(viewModel.activeSeconds))
                Divider()
                StepRow(index: 3, title: "Friction note", estimate: viewModel.detourNote ?? "none yet", tag: viewModel.detourNote == nil ? "optional" : "captured", status: viewModel.detourNote == nil ? .pending : .done)
            }
        }
    }

    private func bottomActionDock(safeAreaBottom: CGFloat) -> some View {
        let attachmentOffset = TimingInstrumentLayout.bottomDockAttachmentOffset(for: safeAreaBottom)
        return VStack(spacing: 9) {
            Capsule()
                .fill(Color(parallax: .separatorLight))
                .frame(
                    width: ParallaxBottomSheetLayout.handleWidth,
                    height: ParallaxBottomSheetLayout.handleHeight
                )
            HStack(spacing: 8) {
                DrawerLauncher(title: "Log friction", subtitle: "What slowed this down", icon: "bubble.left", role: .waiting) {
                    showsFrictionCapture = true
                }
                DrawerLauncher(title: "Insights", subtitle: "What Parallax noticed", icon: "sparkles", role: .checkpoint) {
                    if viewModel.isCheckpointedMode {
                        activeDrawer = .stepDetail
                    } else if viewModel.detourNote != nil {
                        activeDrawer = .frictionEvidence
                    } else {
                        showsStepNoteCapture = true
                    }
                }
            }
        }
        .padding(.top, 10)
        .padding(.horizontal, 10)
        .padding(.bottom, TimingInstrumentLayout.bottomDockBottomPadding(for: safeAreaBottom))
        .frame(maxWidth: .infinity)
        .parallaxBottomAttachedSheet(
            topCornerRadius: 22,
            shadowOpacity: 0.055,
            shadowRadius: 10,
            shadowY: -3
        )
        .offset(y: attachmentOffset)
    }

    @ViewBuilder
    private func sessionDrawerOverlay(_ drawer: Phase8DrawerWorkflow) -> some View {
        switch drawer {
        case .stepDetail:
            StepDetailDrawerView(detail: viewModel.stepDetail) { action in
                Task {
                    await perform(action)
                    activeDrawer = nil
                }
            } dismiss: {
                activeDrawer = nil
            }
        case .frictionEvidence:
            FrictionEvidenceDrawerView(evidence: viewModel.frictionEvidence) { action in
                Task {
                    await perform(action)
                    activeDrawer = nil
                }
            } dismiss: {
                activeDrawer = nil
            }
        case .forgottenTimer, .reviewDecision, .preflightEvidence, .checkpointSetup:
            EmptyView()
        }
    }

    private func perform(_ action: Phase8DrawerAction) async {
        switch action {
        case .completeStep:
            await viewModel.completeCurrentCheckpoint()
        case .pauseStep:
            await viewModel.pauseCurrentStep()
        case .skipStep:
            await viewModel.skipCurrentCheckpoint()
        case .moveStep:
            await viewModel.moveCurrentCheckpoint()
        case .addStepNote:
            showsStepNoteCapture = true
        case .confirmFrictionEvidence:
            guard let resourceName = viewModel.detourResourceName,
                  let note = viewModel.detourNote
            else {
                showsFrictionCapture = true
                return
            }
            await viewModel.confirmFrictionEvidence(
                resourceName: resourceName,
                note: note,
                suggestedPreflightText: nil
            )
        case .correctFrictionEvidence:
            await viewModel.correctFrictionEvidence()
        case .ignoreFrictionEvidence:
            await viewModel.ignoreFrictionEvidence()
        case .keepFrictionNoteOnly:
            await viewModel.keepFrictionNoteOnly()
        case .trimForgottenTimer, .timerKeptRunning, .forgottenTimerNotSure,
             .saveUsefulRun, .markUnusual, .savePartial, .activeTimeOnly,
             .frictionEvidenceOnly, .queryEvidenceOnly, .discardTimingKeepNote,
             .discardAll, .keepPreflightActive,
             .snoozePreflight, .hidePreflight, .retirePreflight, .viewPreflightRuns,
             .updateCheckpointPlan, .makeCheckpointOptional, .startFromCheckpoint:
            break
        }
    }
}

private struct TimingRailBadge: View {
    let text: String
    let systemName: String
    let role: TemporalSemanticRole

    var body: some View {
        Label {
            Text(text)
                .lineLimit(1)
                .minimumScaleFactor(0.75)
        } icon: {
            Image(systemName: systemName)
                .font(.system(size: 10.2, weight: .semibold))
        }
        .font(.system(size: TimingInstrumentLayout.badgeFontSize, weight: .semibold, design: .rounded))
        .padding(.horizontal, 8)
        .frame(minHeight: TimingInstrumentLayout.badgeMinHeight)
        .background(Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)))
        .foregroundStyle(Color(parallax: DesignTokenMapper.colorToken(for: role)))
        .clipShape(Capsule())
        .overlay(Capsule().stroke(Color(parallax: .separatorLight).opacity(0.5), lineWidth: 1))
    }
}

private struct FrictionCaptureDrawerView: View {
    let activityName: String
    let existingNote: String?
    let dismiss: () -> Void
    let save: (_ resourceName: String, _ note: String) -> Void

    @State private var resourceName = ""
    @State private var note = ""

    private var trimmedNote: String {
        note.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 520, dismiss: dismiss) { _ in
            VStack(alignment: .leading, spacing: 14) {
                Text("Log friction")
                    .font(.system(size: 25, weight: .bold, design: .rounded))
                    .foregroundStyle(Color(parallax: .textPrimaryLight))
                Text(activityName)
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color(parallax: .detourText))
                    .lineLimit(2)
                Text("Capture what slowed this run down. The raw note is saved as a private annotation, then the detour is queued as wall-only friction.")
                    .font(.system(size: 13, weight: .regular, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
                    .fixedSize(horizontal: false, vertical: true)

                VStack(alignment: .leading, spacing: 10) {
                    TextField("Resource or blocker", text: $resourceName)
                        .textFieldStyle(.roundedBorder)
                        .accessibilityLabel("Resource or blocker")
                    TextField("What slowed this down?", text: $note, axis: .vertical)
                        .lineLimit(3...5)
                        .textFieldStyle(.roundedBorder)
                        .accessibilityLabel("What slowed this down?")
                }
                .padding(14)
                .background(Color(parallax: .elevatedLight))
                .clipShape(RoundedRectangle(cornerRadius: 18))

                if let existingNote {
                    Label(existingNote, systemImage: "checkmark.circle")
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                        .lineLimit(2)
                }

                HStack(spacing: 9) {
                    Button {
                        dismiss()
                    } label: {
                        Text("Cancel")
                            .font(.system(size: 13, weight: .semibold, design: .rounded))
                            .frame(maxWidth: .infinity, minHeight: 42)
                    }
                    .buttonStyle(.bordered)

                    Button {
                        save(resourceName, trimmedNote)
                    } label: {
                        Label("Save friction", systemImage: "tray.and.arrow.down")
                            .font(.system(size: 13, weight: .bold, design: .rounded))
                            .frame(maxWidth: .infinity, minHeight: 42)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(trimmedNote.isEmpty)
                }
            }
            .padding(.top, 34)
            .padding(.horizontal, 20)
        }
    }
}

private struct TimingRing: View {
    let elapsedSeconds: Int
    let activeSeconds: Int

    private var activeShare: CGFloat {
        guard elapsedSeconds > 0 else { return 0 }
        let ratio = Double(activeSeconds) / Double(max(elapsedSeconds, 1))
        return CGFloat(min(max(ratio, 0), 1))
    }

    private var activeShareText: String {
        "\(Int((activeShare * 100).rounded()))% active"
    }

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color(parallax: .separatorLight), lineWidth: 10)
            Circle()
                .stroke(Color(parallax: .activeSoft), lineWidth: 4)
                .padding(8)
            Circle()
                .trim(from: 0, to: activeShare)
                .stroke(Color(parallax: .active), style: StrokeStyle(lineWidth: 10, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .opacity(activeShare > 0 ? 1 : 0)
            VStack(spacing: 3) {
                Text("Wall")
                    .font(.system(size: 8, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
                DurationText(seconds: elapsedSeconds)
                    .font(.system(size: 24, weight: .bold, design: .rounded))
                Rectangle()
                    .fill(Color(parallax: .separatorLight))
                    .frame(width: 44, height: 1)
                Text(activeShareText)
                    .font(.system(size: 8, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
                DurationText(seconds: activeSeconds)
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Wall time \(elapsedSeconds) seconds. Active time \(activeSeconds) seconds. \(activeShareText).")
    }
}

private struct SessionPrimaryStepButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: "checkmark.circle")
                .font(.system(size: 14.5, weight: .bold, design: .rounded))
                .lineLimit(1)
                .minimumScaleFactor(0.78)
                .frame(maxWidth: .infinity, minHeight: TimingInstrumentLayout.primaryButtonHeight)
                .background(Color(parallax: .active))
                .foregroundStyle(.white)
                .clipShape(Capsule())
        }
        .buttonStyle(.plain)
    }
}

private struct DrawerLauncher: View {
    let title: String
    let subtitle: String
    let icon: String
    let role: TemporalSemanticRole
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                CircleIcon(
                    systemName: icon,
                    tint: Color(parallax: DesignTokenMapper.colorToken(for: role)),
                    fill: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)),
                    size: 30,
                    symbolSize: 13
                )
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 12.2, weight: .bold, design: .rounded))
                        .lineLimit(1)
                    Text(subtitle)
                        .font(.system(size: 10.2, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                        .lineLimit(1)
                        .minimumScaleFactor(0.65)
                }
                Spacer(minLength: 0)
            }
            .padding(8)
            .frame(maxWidth: .infinity, minHeight: 52)
            .background(Color(parallax: .cardLight))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color(parallax: .separatorLight), lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 14))
        }
        .buttonStyle(.plain)
    }
}

private struct CompactLabel: View {
    let text: String
    let systemName: String

    init(_ text: String, systemName: String) {
        self.text = text
        self.systemName = systemName
    }

    var body: some View {
        Label(text, systemImage: systemName)
            .font(.system(size: 9.2, weight: .medium, design: .rounded))
            .foregroundStyle(Color(parallax: .textSecondaryLight))
            .lineLimit(1)
            .minimumScaleFactor(0.65)
    }
}

private struct SessionAction: View {
    let title: String
    let icon: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 3) {
                Image(systemName: icon)
                    .font(.system(size: 13, weight: .semibold))
                Text(title)
                    .font(.system(size: 10.8, weight: .semibold, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
            }
            .frame(maxWidth: .infinity, minHeight: TimingInstrumentLayout.secondaryButtonHeight)
        }
        .buttonStyle(.bordered)
    }
}
