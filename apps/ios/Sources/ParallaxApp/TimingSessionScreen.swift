import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

struct TimingSessionScreen: View {
    @ObservedObject var viewModel: TimingSliceViewModel
    let initialDrawer: String?
    let finishAndReview: () async -> Void
    @State private var activeDrawer: Phase8DrawerWorkflow?
    @State private var presentedInitialDrawer = false

    var body: some View {
        CanonicalScreen(
            title: "Timing Session",
            subtitle: "Learning how this workflow really goes\nQuick taps are enough — I’ll learn from the run.",
            leadingIcon: "chevron.left"
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
            bottomActionDock
        }
        .overlay {
            if let activeDrawer {
                sessionDrawerOverlay(activeDrawer)
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
    }

    private var badgeRail: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 5) {
                SoftBadge(text: "Checkpointed timing", systemName: "checkmark.circle", role: .active)
                SoftBadge(text: "Personal model", systemName: "leaf", role: .detour)
                SoftBadge(text: "Active + elapsed", systemName: "waveform.path.ecg", role: .checkpoint)
                SoftBadge(text: "Low burden", systemName: "heart", role: .checkpoint)
            }
        }
    }

    private var instrumentCard: some View {
        Card {
            GeometryReader { proxy in
                let ringSize = min(max(proxy.size.width * 0.35, 112), 132)
                HStack(alignment: .center, spacing: 10) {
                    TimingRing(elapsedSeconds: viewModel.elapsedSeconds, activeSeconds: viewModel.activeSeconds)
                        .frame(width: ringSize, height: ringSize)
                    VStack(alignment: .leading, spacing: 4) {
                        SoftBadge(text: viewModel.status.rawValue, systemName: nil, role: .active)
                        Text(viewModel.currentCheckpointLabel)
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            .lineLimit(2)
                            .minimumScaleFactor(0.72)
                        Text("Checkpoint labels are optional")
                            .font(.system(size: 10.5, weight: .medium, design: .rounded))
                            .foregroundStyle(Color(parallax: .textSecondaryLight))
                        CompactLabel("\(viewModel.elapsedSeconds / 60) min elapsed", systemName: "clock")
                        CompactLabel("\(viewModel.pendingEventCount) queued mutation\(viewModel.pendingEventCount == 1 ? "" : "s")", systemName: "pause.circle")
                        CompactLabel(viewModel.detourNote ?? "No friction note yet", systemName: "progress.indicator")
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .frame(height: 132)
            SessionPrimaryStepButton(title: "Done with this step") {
                Task { await viewModel.completeCurrentCheckpoint() }
            }
            HStack(spacing: 7) {
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
                    activeDrawer = .frictionEvidence
                }
                SessionAction(title: "Skip", icon: "forward") {
                    Task { await viewModel.skipCurrentCheckpoint() }
                }
                SessionAction(title: "Move", icon: "arrow.up.arrow.down") {
                    Task { await viewModel.moveCurrentCheckpoint() }
                }
            }
        }
    }

    private var stepPreviewCard: some View {
        Card {
            StepRow(index: 1, title: "Start activity", estimate: "timed now", tag: "source event", status: .done)
            Divider()
            StepRow(index: 2, title: viewModel.currentCheckpointLabel, estimate: "active now", tag: "current", status: .running)
            Divider()
            StepRow(index: 3, title: viewModel.nextCheckpointLabel, estimate: "optional", tag: "pending", status: .pending)
            Button {
                activeDrawer = .stepDetail
            } label: {
                Label("Show all steps", systemImage: "list.bullet")
                    .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                    .frame(maxWidth: .infinity, minHeight: 30)
            }
            .buttonStyle(.bordered)
        }
    }

    private var bottomActionDock: some View {
        VStack(spacing: 9) {
            Capsule()
                .fill(Color(parallax: .separatorLight))
                .frame(width: 42, height: 4)
            HStack(spacing: 8) {
                DrawerLauncher(title: "Log friction", subtitle: "What slowed this down", icon: "bubble.left", role: .waiting) {
                    activeDrawer = .frictionEvidence
                }
                DrawerLauncher(title: "Insights", subtitle: "What Parallax noticed", icon: "sparkles", role: .checkpoint) {
                    activeDrawer = .stepDetail
                }
            }
            HStack(spacing: 8) {
                Button {
                    Task { await finishAndReview() }
                } label: {
                    Label("Finish + review", systemImage: "checkmark.circle")
                        .font(.system(size: 13.5, weight: .bold, design: .rounded))
                        .lineLimit(1)
                        .frame(maxWidth: .infinity, minHeight: 38)
                }
                .buttonStyle(.borderedProminent)

                Button {
                    activeDrawer = .stepDetail
                } label: {
                    Label("More", systemImage: "ellipsis")
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                        .frame(width: 92, height: 38)
                }
                .buttonStyle(.bordered)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity)
        .background(Color(parallax: .elevatedLight).opacity(0.96))
        .overlay(RoundedRectangle(cornerRadius: 22).stroke(Color(parallax: .separatorLight), lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 22))
        .shadow(color: .black.opacity(0.045), radius: 10, y: 3)
    }

    @ViewBuilder
    private func sessionDrawerOverlay(_ drawer: Phase8DrawerWorkflow) -> some View {
        switch drawer {
        case .stepDetail:
            StepDetailDrawerView { action in
                Task {
                    await perform(action)
                    activeDrawer = nil
                }
            }
        case .frictionEvidence:
            FrictionEvidenceDrawerView { action in
                Task {
                    await perform(action)
                    activeDrawer = nil
                }
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
            await viewModel.captureStepNote()
        case .confirmFrictionEvidence:
            await viewModel.confirmFrictionEvidence(
                resourceName: "missing resource",
                note: viewModel.detourNote ?? "Confirmed friction evidence.",
                suggestedPreflightText: nil
            )
        case .correctFrictionEvidence:
            await viewModel.correctFrictionEvidence()
        case .ignoreFrictionEvidence:
            await viewModel.ignoreFrictionEvidence()
        case .keepFrictionNoteOnly:
            await viewModel.keepFrictionNoteOnly()
        case .trimForgottenTimer, .timerKeptRunning, .forgottenTimerNotSure, .saveUsefulRun, .markUnusual,
             .activeTimeOnly, .frictionEvidenceOnly, .discardTimingKeepNote, .keepPreflightActive,
             .snoozePreflight, .hidePreflight, .retirePreflight, .viewPreflightRuns,
             .updateCheckpointPlan, .makeCheckpointOptional, .startFromCheckpoint:
            break
        }
    }
}

private struct TimingRing: View {
    let elapsedSeconds: Int
    let activeSeconds: Int

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color(parallax: .activeSoft), lineWidth: 9)
            Circle()
                .trim(from: 0.02, to: 0.78)
                .stroke(Color(parallax: .active), style: StrokeStyle(lineWidth: 9, lineCap: .round))
                .rotationEffect(.degrees(-90))
            VStack(spacing: 4) {
                Text("Elapsed wall time")
                    .font(.system(size: 8, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
                DurationText(seconds: elapsedSeconds)
                    .font(.system(size: 24, weight: .bold, design: .rounded))
                Rectangle()
                    .fill(Color(parallax: .separatorLight))
                    .frame(width: 44, height: 1)
                Text("Active time")
                    .font(.system(size: 8, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
                DurationText(seconds: activeSeconds)
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
            }
        }
    }
}

private struct SessionPrimaryStepButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: "checkmark.circle")
                .font(.system(size: 13.5, weight: .bold, design: .rounded))
                .lineLimit(1)
                .frame(maxWidth: .infinity, minHeight: 38)
        }
        .buttonStyle(.borderedProminent)
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
                        .font(.system(size: 11.5, weight: .bold, design: .rounded))
                        .lineLimit(1)
                    Text(subtitle)
                        .font(.system(size: 8.8, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                        .lineLimit(1)
                        .minimumScaleFactor(0.65)
                }
                Spacer(minLength: 0)
            }
            .padding(8)
            .frame(maxWidth: .infinity, minHeight: 48)
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
            Label(title, systemImage: icon)
                .font(.system(size: 8.8, weight: .semibold, design: .rounded))
                .lineLimit(1)
                .minimumScaleFactor(0.55)
                .frame(maxWidth: .infinity, minHeight: 28)
        }
        .buttonStyle(.bordered)
    }
}
