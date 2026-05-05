import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

struct TimingReviewScreen: View {
    @ObservedObject var viewModel: TimingSliceViewModel
    let initialDrawer: String?
    let saveReview: () async -> Void
    let goBack: () -> Void
    @State private var activeDrawer: Phase8DrawerWorkflow?
    @State private var presentedInitialDrawer = false

    var body: some View {
        CanonicalScreen(
            title: "Timing Review",
            subtitle: "Let’s save what actually happened.",
            leadingIcon: "chevron.left",
            leadingAction: goBack
        ) {
            summaryCard
            estimateCard
            reviewBottomDock
        }
        .overlay {
            if let activeDrawer {
                reviewDrawerOverlay(activeDrawer)
            }
        }
        .task {
            guard !presentedInitialDrawer else { return }
            presentedInitialDrawer = true
            if let initialDrawer, let drawer = Phase8DrawerWorkflow(rawDemoValue: initialDrawer),
               drawer == .forgottenTimer || drawer == .reviewDecision {
                activeDrawer = drawer
            }
        }
    }

    private var summaryCard: some View {
        Card {
            HStack(spacing: 11) {
                CircleIcon(systemName: "sparkles", tint: Color(parallax: .detourText), fill: Color(parallax: .detourSoft), size: 44, symbolSize: 20)
                VStack(alignment: .leading, spacing: 3) {
                    Text(viewModel.activityName)
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                    Text("Review decides what this run teaches")
                        .font(.system(size: 10.5, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundStyle(Color(parallax: .textTertiaryLight))
            }
            HStack(spacing: 0) {
                SummaryMetric(icon: "clock", title: "Actual elapsed", value: minutes(viewModel.elapsedSeconds), role: .active)
                Divider()
                SummaryMetric(icon: "leaf", title: "Active time", value: minutes(viewModel.activeSeconds), role: .detour)
                Divider()
                SummaryMetric(icon: "pause.circle", title: "Friction", value: minutes(viewModel.detourSeconds), role: .checkpoint)
                Divider()
                SummaryMetric(icon: "shield", title: "Confidence", value: "Useful run", role: .interruption)
            }
        }
    }

    private var estimateCard: some View {
        Card {
            Text("Estimate vs actual")
                .font(.system(size: 12.5, weight: .semibold, design: .rounded))
            HStack(alignment: .top) {
                VStack(alignment: .leading) {
                    Text("Expected range")
                    Text("Needs data")
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundStyle(Color(parallax: .active))
                }
                Spacer()
                VStack {
                    Text("Actual")
                    Text(minutes(viewModel.elapsedSeconds))
                        .font(.system(size: 17, weight: .bold, design: .rounded))
                        .foregroundStyle(Color(parallax: .checkpointText))
                }
                Spacer()
                VStack(alignment: .leading) {
                    Text("Difference")
                    Text("Review")
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundStyle(Color(parallax: .checkpointText))
                    Text("range updates after review")
                        .font(.caption)
                }
            }
            ProgressView(value: 0.76)
                .tint(Color(parallax: .active))
        }
        .font(.system(size: 10.5, weight: .medium, design: .rounded))
        .foregroundStyle(Color(parallax: .textSecondaryLight))
    }

    private var reviewDrawerGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
            ReviewDrawerLauncher(title: "What happened", subtitle: "Choose all that apply", icon: "checklist", role: .active) {
                activeDrawer = .reviewDecision
            }
            ReviewDrawerLauncher(title: "Time review", subtitle: "Exclude or mark typical", icon: "clock.badge.checkmark", role: .checkpoint) {
                activeDrawer = .forgottenTimer
            }
            ReviewDrawerLauncher(title: "Step breakdown", subtitle: "Review step timings", icon: "list.bullet.rectangle", role: .detour) {
                activeDrawer = .reviewDecision
            }
            ReviewDrawerLauncher(title: "Privacy", subtitle: "What updates the model", icon: "lock", role: .waiting) {
                activeDrawer = .reviewDecision
            }
        }
    }

    private var reviewBottomDock: some View {
        VStack(spacing: 9) {
            Capsule()
                .fill(Color(parallax: .separatorLight))
                .frame(width: 42, height: 4)
            reviewDrawerGrid
            VStack(spacing: 8) {
                HStack {
                    Label("Saved to your personal timing model.", systemImage: "lock")
                    Spacer()
                    Text("Only personal estimates update.")
                }
                .font(.system(size: 9.5, weight: .medium, design: .rounded))
                .foregroundStyle(Color(parallax: .textSecondaryLight))

                HStack(spacing: 8) {
                    Button {
                        activeDrawer = .reviewDecision
                    } label: {
                        Text(viewModel.reviewDecision == .saveUsefulRun ? "Saved" : "Save to model")
                            .font(.system(size: 13.5, weight: .bold, design: .rounded))
                            .lineLimit(1)
                            .frame(maxWidth: .infinity, minHeight: 38)
                    }
                    .buttonStyle(.borderedProminent)
                    Button {
                        Task { await viewModel.saveReviewDecision(.markUnusual) }
                    } label: {
                        Text("Mark unusual")
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .frame(maxWidth: .infinity, minHeight: 38)
                    }
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .buttonStyle(.bordered)
                        .frame(maxWidth: .infinity, minHeight: 38)
                    Button {
                        Task { await viewModel.discardTimingKeepNote() }
                    } label: {
                        Text("Discard")
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .frame(maxWidth: .infinity, minHeight: 38)
                    }
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .buttonStyle(.bordered)
                        .frame(maxWidth: .infinity, minHeight: 38)
                }
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
    private func reviewDrawerOverlay(_ drawer: Phase8DrawerWorkflow) -> some View {
        switch drawer {
        case .forgottenTimer:
            ForgottenTimerDrawerView { action in
                Task {
                    await perform(action)
                    activeDrawer = nil
                }
            }
        case .reviewDecision:
            ReviewDecisionDrawerView(selectedDecision: viewModel.reviewDecision ?? .saveUsefulRun) { decision in
                Task {
                    await viewModel.saveReviewDecision(decision)
                    activeDrawer = nil
                }
            }
        case .stepDetail, .frictionEvidence, .preflightEvidence, .checkpointSetup:
            EmptyView()
        }
    }

    private func perform(_ action: Phase8DrawerAction) async {
        switch action {
        case .trimForgottenTimer:
            await viewModel.trimForgottenTimerAtPlaceChange()
        case .timerKeptRunning:
            await viewModel.timerKeptRunningAfterPlaceChange()
        case .discardTimingKeepNote:
            await viewModel.discardTimingKeepNote()
        case .forgottenTimerNotSure:
            await viewModel.deferForgottenTimerDecision()
        case .completeStep, .pauseStep, .skipStep, .moveStep, .addStepNote,
             .confirmFrictionEvidence, .correctFrictionEvidence, .ignoreFrictionEvidence,
             .keepFrictionNoteOnly, .saveUsefulRun, .markUnusual, .activeTimeOnly,
             .frictionEvidenceOnly, .keepPreflightActive, .snoozePreflight, .hidePreflight,
             .retirePreflight, .viewPreflightRuns, .updateCheckpointPlan,
             .makeCheckpointOptional, .startFromCheckpoint:
            break
        }
    }

    private func minutes(_ seconds: Int) -> String {
        "\(max(0, seconds / 60)) min"
    }
}

private struct ReviewDrawerLauncher: View {
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

private struct SummaryMetric: View {
    let icon: String
    let title: String
    let value: String
    let role: TemporalSemanticRole

    var body: some View {
        VStack(spacing: 4) {
            CircleIcon(systemName: icon, tint: Color(parallax: DesignTokenMapper.colorToken(for: role)), fill: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)), size: 28, symbolSize: 12)
            Text(title)
                .font(.system(size: 8.8, weight: .medium, design: .rounded))
                .foregroundStyle(Color(parallax: .textSecondaryLight))
                .multilineTextAlignment(.center)
                .lineLimit(2)
                .minimumScaleFactor(0.6)
            Text(value)
                .font(.system(size: 11.5, weight: .bold, design: .rounded))
                .foregroundStyle(Color(parallax: DesignTokenMapper.colorToken(for: role)))
                .multilineTextAlignment(.center)
                .lineLimit(2)
                .minimumScaleFactor(0.68)
        }
        .frame(maxWidth: .infinity)
    }
}
