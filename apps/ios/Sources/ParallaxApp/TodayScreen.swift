import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

struct TodayScreen: View {
    @ObservedObject var viewModel: TimingSliceViewModel
    @Binding var showsLauncher: Bool
    let initialDrawer: String?
    let startTiming: () async -> Void
    @State private var activeDrawer: Phase8DrawerWorkflow?
    @State private var presentedInitialDrawer = false

    var body: some View {
        CanonicalScreen(title: "Today", subtitle: "Tuesday, April 22", leadingIcon: "line.3.horizontal") {
            currentFocusCard
            guidanceCard
            planCard
            quickCaptureCard
            resetActions
        }
        .overlay(alignment: .bottom) {
            if showsLauncher {
                TimingLauncherSheet(
                    activityName: viewModel.activityName,
                    startTiming: startTiming,
                    dismiss: { showsLauncher = false }
                )
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .overlay {
            if activeDrawer == .preflightEvidence {
                PreflightEvidenceDrawerView { decision in
                    Task {
                        await viewModel.decidePreflightCheck(decision)
                        activeDrawer = nil
                    }
                }
            }
        }
        .task {
            guard !presentedInitialDrawer else { return }
            presentedInitialDrawer = true
            if let initialDrawer, Phase8DrawerWorkflow(rawDemoValue: initialDrawer) == .preflightEvidence {
                activeDrawer = .preflightEvidence
            }
        }
    }

    private var currentFocusCard: some View {
        Card(background: Color(parallax: .activeSoft).opacity(0.46)) {
            Text("CURRENT FOCUS")
                .font(.system(size: 9, weight: .bold, design: .rounded))
                .tracking(2)
                .foregroundStyle(Color(parallax: .activeText))
            HStack(spacing: 10) {
                ZStack {
                    Circle().fill(Color(parallax: .activeSoft))
                    Circle().stroke(Color(parallax: .active).opacity(0.25), lineWidth: 7)
                    Circle().fill(Color(parallax: .active))
                        .frame(width: 28, height: 28)
                    Image(systemName: "checkmark")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(.white)
                }
                .frame(width: 52, height: 52)

                VStack(alignment: .leading, spacing: 3) {
                    Text("Get dressed and leave for therapy")
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .foregroundStyle(Color(parallax: .textPrimaryLight))
                        .lineLimit(2)
                        .minimumScaleFactor(0.7)
                    Text("Estimated 12 min  ·  helps you get unstuck")
                        .font(.system(size: 10.5, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                        .lineLimit(2)
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundStyle(Color(parallax: .textTertiaryLight))
            }
            ProgressView(value: 0.36)
                .tint(Color(parallax: .active))
            Button {
                showsLauncher = true
            } label: {
                Text("Best next step right now")
                    .font(.system(size: 10.5, weight: .semibold, design: .rounded))
                    .frame(maxWidth: .infinity)
            }
        }
    }

    private var guidanceCard: some View {
        Card {
            HStack(spacing: 10) {
                CircleIcon(systemName: "leaf", tint: Color(parallax: .detourText), fill: Color(parallax: .detourSoft), size: 38, symbolSize: 15)
                VStack(alignment: .leading, spacing: 3) {
                    Text("Start the timer, then tell Parallax what changed.")
                        .font(.system(size: 12.5, weight: .semibold, design: .rounded))
                        .lineLimit(2)
                    Text("Offline is fine · review decides what the app learns")
                        .font(.system(size: 10, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .detourText))
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                }
                Spacer()
                Image(systemName: "heart.fill")
                    .foregroundStyle(Color(parallax: .detourText))
            }
            Button {
                activeDrawer = .preflightEvidence
            } label: {
                Label("Review sponge preflight check", systemImage: "sparkles")
                    .font(.system(size: 10.5, weight: .semibold, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.74)
                    .frame(maxWidth: .infinity, minHeight: 30)
            }
            .buttonStyle(.bordered)
        }
    }

    private var planCard: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text("Timing loop")
                    .font(.system(size: 12.5, weight: .semibold, design: .rounded))
                Spacer()
                Text("Adjusting as things change  •")
                    .font(.system(size: 9.5, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
            }
            Card {
                PlanRow(time: "9:15", icon: "pawprint", title: "Dog walk", detail: "15 min", tag: "High energy", role: .detour)
                Divider()
                PlanRow(time: "10:30", icon: "calendar", title: "Therapy appointment", detail: "11:00-12:00 PM", tag: "Time sensitive", role: .active)
                Divider()
                PlanRow(time: "12:15", icon: "fork.knife", title: "Quick lunch", detail: "20 min", tag: "Flexible", role: .interruption)
                Divider()
                PlanRow(time: "1:30", icon: "envelope", title: "Send NC2 follow-up email", detail: "20 min", tag: "Can move", role: .checkpoint)
                Divider()
                PlanRow(time: "4:00", icon: "cart", title: "Grocery stop", detail: "45 min", tag: "Can move", role: .detour)
                Divider()
                PlanRow(time: "7:30", icon: "moon", title: "Evening reset", detail: "20 min", tag: "Low energy", role: .active)
            }
        }
    }

    private var quickCaptureCard: some View {
        Card {
            HStack(spacing: 10) {
                CircleIcon(systemName: "plus", tint: .white, fill: Color(parallax: .active), size: 36, symbolSize: 15)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Quick capture")
                        .font(.system(size: 12.5, weight: .semibold, design: .rounded))
                    Text("Add a note, detour, or idea...")
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

    private var resetActions: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Need a reset?")
                .font(.system(size: 10.5, weight: .medium, design: .rounded))
                .foregroundStyle(Color(parallax: .textSecondaryLight))
            HStack(spacing: 8) {
                ResetAction(title: "Replan from here", subtitle: "Adjust the rest of today", icon: "arrow.clockwise", role: .active)
                ResetAction(title: "Make this easier", subtitle: "Simplify and focus", icon: "leaf", role: .detour)
            }
        }
    }
}

private struct PlanRow: View {
    let time: String
    let icon: String
    let title: String
    let detail: String
    let tag: String
    let role: TemporalSemanticRole

    var body: some View {
        HStack(spacing: 8) {
            Text(time)
                .font(.system(size: 9.5, weight: .medium, design: .rounded))
                .foregroundStyle(Color(parallax: .textSecondaryLight))
                .frame(width: 30, alignment: .leading)
            CircleIcon(systemName: icon, tint: Color(parallax: DesignTokenMapper.colorToken(for: role)), fill: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)), size: 28, symbolSize: 12)
            VStack(alignment: .leading, spacing: 1) {
                Text(title)
                    .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                Text(detail)
                    .font(.system(size: 9.5, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
            }
            Spacer()
            SoftBadge(text: tag, systemName: nil, role: role)
            Image(systemName: "chevron.right")
                .font(.caption.weight(.bold))
                .foregroundStyle(Color(parallax: .textTertiaryLight))
        }
    }
}

private struct ResetAction: View {
    let title: String
    let subtitle: String
    let icon: String
    let role: TemporalSemanticRole

    var body: some View {
        Card {
            HStack(spacing: 8) {
                CircleIcon(systemName: icon, tint: Color(parallax: DesignTokenMapper.colorToken(for: role)), fill: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)), size: 30, symbolSize: 13)
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 10.5, weight: .bold, design: .rounded))
                        .foregroundStyle(Color(parallax: DesignTokenMapper.colorToken(for: role)))
                        .lineLimit(1)
                        .minimumScaleFactor(0.64)
                    Text(subtitle)
                        .font(.system(size: 8.5, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                        .lineLimit(2)
                        .minimumScaleFactor(0.62)
                }
            }
        }
    }
}
