import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

public enum CheckpointSetupPolishLayout {
    public static let contextBadgeImpliesAction = false
    public static let contextBadgeUsesInformationalCopy = true
}

struct CheckpointSetupScreen: View {
    @ObservedObject var viewModel: TimingSliceViewModel
    let initialDrawer: String?
    @State private var activeDrawer: Phase8DrawerWorkflow?
    @State private var presentedInitialDrawer = false

    var body: some View {
        CanonicalScreen(
            title: "Checkpoint timing",
            subtitle: "Optional timing markers for a run.",
            leadingIcon: "chevron.left"
        ) {
            activityHeader
            contextCard
            guidanceCard
            stepsCard
        }
        .safeAreaInset(edge: .bottom) {
            actionRail
                .padding(.horizontal, 14)
                .padding(.top, 8)
                .padding(.bottom, 12)
                .background(Color(parallax: .canvasLight).opacity(0.96))
        }
        .overlay {
            if activeDrawer == .checkpointSetup {
                CheckpointSetupDrawerView { action in
                    Task {
                        await perform(action)
                        activeDrawer = nil
                    }
                } dismiss: {
                    activeDrawer = nil
                }
            }
        }
        .task {
            guard !presentedInitialDrawer else { return }
            presentedInitialDrawer = true
            if let initialDrawer, Phase8DrawerWorkflow(rawDemoValue: initialDrawer) == .checkpointSetup {
                activeDrawer = .checkpointSetup
            }
        }
    }

    private func perform(_ action: Phase8DrawerAction) async {
        switch action {
        case .updateCheckpointPlan:
            await viewModel.updateCheckpointPlan()
        case .makeCheckpointOptional:
            await viewModel.makeCheckpointOptional()
        case .startFromCheckpoint:
            await viewModel.startFromCurrentCheckpoint()
        case .completeStep, .pauseStep, .skipStep, .moveStep, .addStepNote,
             .confirmFrictionEvidence, .correctFrictionEvidence, .ignoreFrictionEvidence,
             .keepFrictionNoteOnly, .trimForgottenTimer, .timerKeptRunning,
             .forgottenTimerNotSure, .saveUsefulRun, .markUnusual, .savePartial,
             .activeTimeOnly, .frictionEvidenceOnly, .queryEvidenceOnly,
             .discardTimingKeepNote, .discardAll, .keepPreflightActive,
             .snoozePreflight, .hidePreflight, .retirePreflight, .viewPreflightRuns:
            break
        }
    }

    private var activityHeader: some View {
        ActivitySummaryRow(
            title: viewModel.activityName,
            subtitle: "Optional checkpoints",
            detail: "Whole-run timing works without checkpoints",
            icon: "timer"
        )
    }

    private var contextCard: some View {
        Card(background: Color(parallax: .checkpointSoft).opacity(0.42)) {
            HStack {
                CircleIcon(
                    systemName: "sparkles",
                    tint: Color(parallax: .checkpointText),
                    fill: Color(parallax: .checkpointSoft),
                    size: 38,
                    symbolSize: 16
                )
                VStack(alignment: .leading, spacing: 3) {
                    Text("Timing context")
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                    Text("Only what explains timing variance.")
                        .font(.system(size: 11, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                }
                Spacer()
                SoftBadge(text: "Optional", systemName: nil, role: .checkpoint)
            }
            Text("Attach context only when it should explain this run's timing.")
                .font(.system(size: 13.5, weight: .regular, design: .rounded))
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(parallax: .elevatedLight))
                .clipShape(RoundedRectangle(cornerRadius: 16))
        }
    }

    private var guidanceCard: some View {
        Card {
            HStack(spacing: 10) {
                CircleIcon(systemName: "leaf", tint: Color(parallax: .detourText), fill: Color(parallax: .detourSoft), size: 42, symbolSize: 18)
                VStack(alignment: .leading, spacing: 3) {
                    Text("Whole-run timing still works.")
                        .font(.system(size: 14.5, weight: .bold, design: .rounded))
                        .foregroundStyle(Color(parallax: .detourText))
                    Text("Checkpoints are optional timing markers.")
                        .font(.system(size: 11, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                }
                Spacer()
                Image(systemName: "heart.fill")
                    .foregroundStyle(Color(parallax: .detourText))
            }
        }
    }

    private var stepsCard: some View {
        Card {
            HStack {
                Text("Timing checkpoints")
                    .font(.system(size: 12.5, weight: .semibold, design: .rounded))
                Spacer()
                Text("Optional before timing")
                    .font(.system(size: 10.5, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
            }
            StepRow(index: 1, title: "Start timer", estimate: "timed now", tag: "source event", status: .running)
            Divider()
            StepRow(index: 2, title: viewModel.currentCheckpointLabel, estimate: "optional", tag: "current", status: .pending)
            Divider()
            StepRow(index: 3, title: viewModel.nextCheckpointLabel, estimate: "optional", tag: "next", status: .pending)
            Divider()
            StepRow(index: 4, title: "Later checkpoint", estimate: "optional", tag: "timing", status: .pending)
            Button {
                activeDrawer = .checkpointSetup
            } label: {
                Text("Open checkpoint timing")
                    .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                    .frame(maxWidth: .infinity, minHeight: 30)
            }
            .buttonStyle(.bordered)
        }
    }

    private var actionRail: some View {
        HStack(spacing: 8) {
            PrimaryButton(title: "Start checkpointed timer", systemName: nil) {
                activeDrawer = .checkpointSetup
            }
            Button {
                activeDrawer = nil
            } label: {
                Text("Back to today")
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .frame(maxWidth: .infinity, minHeight: 40)
            }
                .font(.system(size: 13, weight: .semibold, design: .rounded))
                .buttonStyle(.bordered)
                .frame(maxWidth: .infinity, minHeight: 40)
        }
    }
}
