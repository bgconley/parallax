import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

public enum TimingLauncherSheetLayout {
    public static let bottomSheetUsesOverlayAttachment = true
    public static let bottomSheetExtendsThroughBottomSafeArea = true
    public static let directActionsUseBalancedHeights = true
    public static let directActionHeight: CGFloat = TimingInstrumentLayout.primaryButtonHeight
    public static let directActionCornerRadius: CGFloat = 18

    public static func bottomSheetSafeAreaExtension(for safeAreaBottom: CGFloat) -> CGFloat {
        TimingInstrumentLayout.bottomDockSafeAreaExtension(for: safeAreaBottom)
    }

    public static func bottomSheetAttachmentOffset(for safeAreaBottom: CGFloat) -> CGFloat {
        bottomSheetSafeAreaExtension(for: safeAreaBottom)
    }

    public static func bottomSheetBottomPadding(for safeAreaBottom: CGFloat) -> CGFloat {
        ParallaxBottomSheetLayout.bottomContentPadding
            + bottomSheetSafeAreaExtension(for: safeAreaBottom) * 2
    }
}

struct TimingLauncherSheet: View {
    let activityName: String
    let startTiming: (MeasurementMode) async -> Void
    let dismiss: () -> Void
    @State private var selectedMode: MeasurementMode = .wholeTask

    var body: some View {
        GeometryReader { proxy in
            ZStack(alignment: .bottom) {
                Color.black.opacity(0.42)
                    .ignoresSafeArea()
                    .onTapGesture(perform: dismiss)
                launcherSheetContent(safeAreaBottom: proxy.safeAreaInsets.bottom)
                    .ignoresSafeArea(.container, edges: .bottom)
            }
        }
    }

    private func launcherSheetContent(safeAreaBottom: CGFloat) -> some View {
        let attachmentOffset = TimingLauncherSheetLayout.bottomSheetAttachmentOffset(for: safeAreaBottom)
        return VStack(spacing: 9) {
            Capsule()
                .fill(Color(parallax: .separatorLight))
                .frame(
                    width: ParallaxBottomSheetLayout.handleWidth,
                    height: ParallaxBottomSheetLayout.handleHeight
                )
                .padding(.top, 8)
            VStack(spacing: 2) {
                Text("Calibrate timing")
                    .font(.system(size: 22, weight: .bold, design: .rounded))
                Text("Choose how Parallax should observe this run.")
                    .font(.system(size: 11.5, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
            }
            ActivitySummaryRow(
                title: activityName,
                subtitle: "No reviewed range yet",
                detail: "Start a run to build evidence",
                icon: "sparkles"
            )
            VStack(alignment: .leading, spacing: 0) {
                Text("How should we measure this?")
                    .font(.system(size: 11.5, weight: .medium, design: .rounded))
                    .padding(.horizontal, 4)
                    .padding(.bottom, 4)
                MeasurementOption(selected: selectedMode == .estimateOnly, icon: "clock", title: "Estimate only", detail: "Use what I know already") {
                    selectedMode = .estimateOnly
                }
                Divider()
                MeasurementOption(selected: selectedMode == .wholeTask, icon: "stopwatch", title: "Time once", detail: "Quick start and stop") {
                    selectedMode = .wholeTask
                }
                Divider()
                MeasurementOption(selected: selectedMode == .checkpointed, icon: "chart.line.uptrend.xyaxis", title: "Checkpointed timing", detail: "Compare timing by phase") {
                    selectedMode = .checkpointed
                }
                Divider()
                MeasurementOption(selected: selectedMode == .routine, icon: "list.bullet", title: "Repeated timing", detail: "Use a saved timing pattern") {
                    selectedMode = .routine
                }
                Divider()
                MeasurementOption(selected: selectedMode == .calibration, icon: "scope", title: "Calibration run", detail: "Guess first, compare after") {
                    selectedMode = .calibration
                }
            }
            .padding(8)
            .background(Color(parallax: .cardLight))
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(parallax: .separatorLight), lineWidth: 1))

            HStack(spacing: 10) {
                LauncherSheetButton(title: "Start timing", isPrimary: true) {
                    Task { await startTiming(selectedMode) }
                }
                LauncherSheetButton(title: "Not now", isPrimary: false, action: dismiss)
            }
        }
        .padding(.horizontal, 14)
        .padding(.bottom, TimingLauncherSheetLayout.bottomSheetBottomPadding(for: safeAreaBottom))
        .parallaxBottomAttachedSheet(
            topCornerRadius: 26,
            fill: Color(parallax: .cardLight),
            shadowOpacity: 0.12,
            shadowRadius: 20,
            shadowY: -7
        )
        .offset(y: attachmentOffset)
    }
}

private struct LauncherSheetButton: View {
    let title: String
    let isPrimary: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 14, weight: .bold, design: .rounded))
                .lineLimit(1)
                .minimumScaleFactor(0.78)
                .frame(maxWidth: .infinity, minHeight: TimingLauncherSheetLayout.directActionHeight)
                .foregroundStyle(isPrimary ? Color.white : Color(parallax: .active))
                .background(background)
                .overlay(border)
                .clipShape(RoundedRectangle(cornerRadius: TimingLauncherSheetLayout.directActionCornerRadius))
        }
        .buttonStyle(.plain)
    }

    private var background: Color {
        isPrimary ? Color(parallax: .active) : Color(parallax: .elevatedLight)
    }

    @ViewBuilder
    private var border: some View {
        if !isPrimary {
            RoundedRectangle(cornerRadius: TimingLauncherSheetLayout.directActionCornerRadius)
                .stroke(Color(parallax: .separatorLight), lineWidth: 1)
        }
    }
}

private struct MeasurementOption: View {
    let selected: Bool
    let icon: String
    let title: String
    let detail: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image(systemName: selected ? "largecircle.fill.circle" : "circle")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(selected ? Color(parallax: .active) : Color(parallax: .textTertiaryLight))
                CircleIcon(systemName: icon, tint: Color(parallax: .active), fill: Color(parallax: .activeSoft), size: 30, symbolSize: 13)
                VStack(alignment: .leading, spacing: 1) {
                    Text(title)
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .lineLimit(1)
                        .minimumScaleFactor(0.68)
                    Text(detail)
                        .font(.system(size: 9.5, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                        .lineLimit(1)
                        .minimumScaleFactor(0.68)
                }
                Spacer()
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .background(selected ? Color(parallax: .activeSoft).opacity(0.42) : Color.clear)
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(selected ? Color(parallax: .active) : Color.clear, lineWidth: 1.2))
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(title)
    }
}
