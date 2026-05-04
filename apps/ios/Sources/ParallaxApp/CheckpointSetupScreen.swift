import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

struct CheckpointSetupScreen: View {
    @ObservedObject var viewModel: TimingSliceViewModel
    let initialDrawer: String?
    @State private var activeDrawer: Phase8DrawerWorkflow?
    @State private var presentedInitialDrawer = false

    var body: some View {
        CanonicalScreen(
            title: "Break it down",
            subtitle: "You only need to start the first step.",
            leadingIcon: "chevron.left"
        ) {
            taskHeader
            contextCard
            guidanceCard
            stepsCard
            actionRail
        }
        .overlay {
            if activeDrawer == .checkpointSetup {
                CheckpointSetupDrawerView { action in
                    Task {
                        await perform(action)
                        activeDrawer = nil
                    }
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
             .forgottenTimerNotSure, .saveUsefulRun, .markUnusual, .activeTimeOnly,
             .frictionEvidenceOnly, .discardTimingKeepNote, .keepPreflightActive,
             .snoozePreflight, .hidePreflight, .retirePreflight, .viewPreflightRuns:
            break
        }
    }

    private var taskHeader: some View {
        ActivitySummaryRow(
            title: "Send NC2 follow-up email",
            subtitle: "Estimated 20 min  ·  Feels hard to start",
            detail: "Basis: recent similar writing tasks",
            icon: "envelope"
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
                    Text("Additional context")
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                    Text("Anything important I should factor in?")
                        .font(.system(size: 11, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                }
                Spacer()
                SoftBadge(text: "Add context", systemName: "plus", role: .checkpoint)
            }
            Text("Need to mention the architecture update, ask Alex for feedback, and include the revised timeline.")
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
                    Text("Starting counts.")
                        .font(.system(size: 14.5, weight: .bold, design: .rounded))
                        .foregroundStyle(Color(parallax: .detourText))
                    Text("Doing step 1 is enough for now.")
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
                Text("Steps in order")
                    .font(.system(size: 12.5, weight: .semibold, design: .rounded))
                Spacer()
                Text("Estimated 20 min total")
                    .font(.system(size: 10.5, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
            }
            StepRow(index: 1, title: "Open email draft", estimate: "2 min", tag: "Easiest first", status: .running)
            Divider()
            StepRow(index: 2, title: "Find Alex’s last message", estimate: "2 min", tag: "Low effort", status: .pending)
            Divider()
            StepRow(index: 3, title: "Hand-wash pans", estimate: "5-14 min", tag: "often expands", status: .pending)
            Divider()
            StepRow(index: 4, title: "Write a short opening", estimate: "4 min", tag: "Core step", status: .pending)
            Button {
                activeDrawer = .checkpointSetup
            } label: {
                Text("Open checkpoint details")
                    .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                    .frame(maxWidth: .infinity, minHeight: 30)
            }
            .buttonStyle(.bordered)
        }
    }

    private var actionRail: some View {
        HStack(spacing: 8) {
            PrimaryButton(title: "Start first step", systemName: nil) {
                activeDrawer = .checkpointSetup
            }
            Button("Back to today") {}
                .font(.system(size: 13, weight: .semibold, design: .rounded))
                .buttonStyle(.bordered)
                .frame(maxWidth: .infinity, minHeight: 40)
        }
    }
}
