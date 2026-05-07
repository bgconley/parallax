import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

public enum TimingReviewDockLayout {
    public static let bottomDockUsesOverlayAttachment = true
    public static let bottomDockExtendsThroughBottomSafeArea = true
    public static let bottomDockScrollReservation: CGFloat = 260
    public static let summaryRowShowsNavigationChevron = ParallaxStaticRowAccessoryLayout.nonInteractiveSummaryRowsShowChevron

    public static func bottomDockSafeAreaExtension(for safeAreaBottom: CGFloat) -> CGFloat {
        TimingInstrumentLayout.bottomDockSafeAreaExtension(for: safeAreaBottom)
    }

    public static func bottomDockAttachmentOffset(for safeAreaBottom: CGFloat) -> CGFloat {
        bottomDockSafeAreaExtension(for: safeAreaBottom)
    }

    public static func bottomDockBottomPadding(for safeAreaBottom: CGFloat) -> CGFloat {
        ParallaxBottomSheetLayout.bottomContentPadding
            + bottomDockSafeAreaExtension(for: safeAreaBottom) * 2
    }
}

public enum TimingReviewEstimateLayout {
    public static let valueFontSize: CGFloat = 14
    public static let supportingCaptionFontSize: CGFloat = 10.5
    public static let supportingCaptionLineLimit = 2
    public static let supportingCaptionMinimumScaleFactor: CGFloat = 0.72
    public static let supportingCaptionCapsAccessibilityScaling = true
}

struct TimingReviewScreen: View {
    @ObservedObject var viewModel: TimingSliceViewModel
    let initialDrawer: String?
    let saveReview: () async -> Void
    let goBack: () -> Void
    @State private var activeDrawer: Phase8DrawerWorkflow?
    @State private var presentedInitialDrawer = false

    var body: some View {
        GeometryReader { proxy in
            ZStack(alignment: .bottom) {
                CanonicalScreen(
                    title: "Timing Review",
                    subtitle: "Let’s save what actually happened.",
                    leadingIcon: "chevron.left",
                    leadingAction: goBack
                ) {
                    summaryCard
                    estimateCard
                    Color.clear
                        .frame(height: TimingReviewDockLayout.bottomDockScrollReservation)
                }
                reviewBottomDock(safeAreaBottom: proxy.safeAreaInsets.bottom)
                    .ignoresSafeArea(.container, edges: .bottom)
            }
            .background(Color(parallax: .canvasLight).ignoresSafeArea())
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
                if drawer == .forgottenTimer {
                    await viewModel.refreshForgottenTimerEvidence()
                }
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
                        .lineLimit(2)
                        .minimumScaleFactor(0.82)
                    Text("Review decides what this run teaches")
                        .font(.system(size: 10.5, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                }
                Spacer()
                if TimingReviewDockLayout.summaryRowShowsNavigationChevron {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(Color(parallax: .textTertiaryLight))
                }
            }
            HStack(spacing: 0) {
                SummaryMetric(icon: "clock", title: "Actual elapsed", value: minutes(viewModel.elapsedSeconds), role: .active)
                Divider()
                SummaryMetric(icon: "leaf", title: "Active time", value: minutes(viewModel.activeSeconds), role: .detour)
                Divider()
                SummaryMetric(icon: "pause.circle", title: "Friction", value: minutes(viewModel.detourSeconds), role: .checkpoint)
                Divider()
                SummaryMetric(icon: "shield", title: "Decision", value: reviewDecisionLabel, role: .interruption)
            }
        }
    }

    private var reviewDecisionLabel: String {
        guard let decision = viewModel.reviewDecision else {
            return "Needs review"
        }
        switch decision {
        case .saveUsefulRun:
            return "Useful run"
        case .markUnusual:
            return "Unusual"
        case .activeOnly:
            return "Active only"
        case .frictionOnly:
            return "Friction only"
        case .discardTimingKeepNote:
            return "Discarded"
        case .discardAll:
            return "Discard all"
        case .savePartial:
            return "Partial"
        case .queryEvidenceOnly:
            return "Evidence only"
        }
    }

    private var reviewFooterPrimary: String {
        switch viewModel.reviewDecision {
        case .discardTimingKeepNote, .discardAll:
            return "Timing excluded from the model."
        case .activeOnly:
            return "Only active duration updates."
        case .frictionOnly:
            return "Only friction evidence updates."
        case .markUnusual:
            return "Saved as unusual evidence."
        case .saveUsefulRun:
            return "Saved to your personal timing model."
        case .savePartial:
            return "Saved as a partial run."
        case .queryEvidenceOnly:
            return "Kept for grounded answers only."
        case nil:
            return "Review decides model inclusion."
        }
    }

    private var reviewFooterSecondary: String {
        switch viewModel.reviewDecision {
        case .discardTimingKeepNote:
            return "Source note can still be kept."
        case .discardAll:
            return "Excluded from normal learning."
        case nil:
            return "Only personal estimates update."
        default:
            return "Only personal estimates update."
        }
    }

    private var saveButtonTitle: String {
        viewModel.reviewDecision == .saveUsefulRun ? "Saved" : "Save run"
    }

    private var unusualButtonTitle: String {
        viewModel.reviewDecision == .markUnusual ? "Marked" : "Mark unusual"
    }

    private var discardButtonTitle: String {
        guard let decision = viewModel.reviewDecision, decision.isDiscardDecision else {
            return "Discard"
        }
        return "Discarded"
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
                        .font(.system(size: TimingReviewEstimateLayout.valueFontSize, weight: .bold, design: .rounded))
                        .foregroundStyle(Color(parallax: .checkpointText))
                    Text("range updates after review")
                        .font(.system(size: TimingReviewEstimateLayout.supportingCaptionFontSize, weight: .medium, design: .rounded))
                        .lineLimit(TimingReviewEstimateLayout.supportingCaptionLineLimit)
                        .minimumScaleFactor(TimingReviewEstimateLayout.supportingCaptionMinimumScaleFactor)
                        .dynamicTypeSize(.xSmall ... .xxxLarge)
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
                Task {
                    await viewModel.refreshForgottenTimerEvidence()
                    activeDrawer = .forgottenTimer
                }
            }
            ReviewDrawerLauncher(title: "Checkpoint review", subtitle: "Review phase timing", icon: "list.bullet.rectangle", role: .detour) {
                activeDrawer = .reviewDecision
            }
            ReviewDrawerLauncher(title: "Privacy", subtitle: "What updates the model", icon: "lock", role: .waiting) {
                activeDrawer = .reviewDecision
            }
        }
    }

    private func reviewBottomDock(safeAreaBottom: CGFloat) -> some View {
        let attachmentOffset = TimingReviewDockLayout.bottomDockAttachmentOffset(for: safeAreaBottom)
        return VStack(spacing: 9) {
            Capsule()
                .fill(Color(parallax: .separatorLight))
                .frame(
                    width: ParallaxBottomSheetLayout.handleWidth,
                    height: ParallaxBottomSheetLayout.handleHeight
                )
            reviewDrawerGrid
            VStack(spacing: 8) {
                HStack {
                    Label(reviewFooterPrimary, systemImage: "lock")
                    Spacer()
                    Text(reviewFooterSecondary)
                }
                .font(.system(size: 9.5, weight: .medium, design: .rounded))
                .foregroundStyle(Color(parallax: .textSecondaryLight))

                HStack(spacing: 8) {
                    Button {
                        activeDrawer = .reviewDecision
                    } label: {
                        Text(saveButtonTitle)
                            .font(.system(size: 13.5, weight: .bold, design: .rounded))
                            .lineLimit(1)
                            .frame(maxWidth: .infinity, minHeight: 38)
                    }
                    .buttonStyle(.borderedProminent)
                    Button {
                        Task { await viewModel.saveReviewDecision(.markUnusual) }
                    } label: {
                        Text(unusualButtonTitle)
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .lineLimit(1)
                            .minimumScaleFactor(0.7)
                            .frame(maxWidth: .infinity, minHeight: 38)
                    }
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .buttonStyle(.bordered)
                        .frame(maxWidth: .infinity, minHeight: 38)
                    Button {
                        Task { await viewModel.discardTimingKeepNote() }
                    } label: {
                        Text(discardButtonTitle)
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .lineLimit(1)
                            .minimumScaleFactor(0.7)
                            .frame(maxWidth: .infinity, minHeight: 38)
                    }
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .buttonStyle(.bordered)
                        .frame(maxWidth: .infinity, minHeight: 38)
                }
            }
        }
        .padding(.top, 10)
        .padding(.horizontal, 10)
        .padding(.bottom, TimingReviewDockLayout.bottomDockBottomPadding(for: safeAreaBottom))
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
    private func reviewDrawerOverlay(_ drawer: Phase8DrawerWorkflow) -> some View {
        switch drawer {
        case .forgottenTimer:
            ForgottenTimerDrawerView(evidence: viewModel.forgottenTimerEvidence) { action in
                Task {
                    await perform(action)
                    activeDrawer = nil
                }
            } dismiss: {
                activeDrawer = nil
            }
        case .reviewDecision:
            ReviewDecisionDrawerView(selectedDecision: viewModel.reviewDecision ?? .saveUsefulRun) { decision in
                Task {
                    await viewModel.saveReviewDecision(decision)
                    activeDrawer = nil
                }
            } dismiss: {
                activeDrawer = nil
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
             .keepFrictionNoteOnly, .saveUsefulRun, .markUnusual, .savePartial,
             .activeTimeOnly, .frictionEvidenceOnly, .queryEvidenceOnly,
             .discardAll, .keepPreflightActive, .snoozePreflight,
             .hidePreflight, .retirePreflight, .viewPreflightRuns,
             .updateCheckpointPlan, .makeCheckpointOptional, .startFromCheckpoint:
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
