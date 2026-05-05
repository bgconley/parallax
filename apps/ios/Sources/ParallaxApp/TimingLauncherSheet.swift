import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

struct TimingLauncherSheet: View {
    let activityName: String
    let startTiming: (MeasurementMode) async -> Void
    let dismiss: () -> Void
    @State private var selectedMode: MeasurementMode = .wholeTask

    var body: some View {
        ZStack(alignment: .bottom) {
            Color.black.opacity(0.42)
                .ignoresSafeArea()
                .onTapGesture(perform: dismiss)
            VStack(spacing: 9) {
                Capsule()
                    .fill(Color(parallax: .separatorLight))
                    .frame(width: 72, height: 5)
                    .padding(.top, 8)
                VStack(spacing: 2) {
                    Text("Calibrate timing")
                        .font(.system(size: 22, weight: .bold, design: .rounded))
                    Text("Choose a low-friction way to learn how this really goes.")
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
                    MeasurementOption(selected: selectedMode == .checkpointed, icon: "chart.line.uptrend.xyaxis", title: "Checkpointed timing", detail: "Learn the steps inside this workflow") {
                        selectedMode = .checkpointed
                    }
                    Divider()
                    MeasurementOption(selected: selectedMode == .routine, icon: "list.bullet", title: "Routine run", detail: "Follow a saved sequence") {
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
                    PrimaryButton(title: "Start timing", systemName: nil) {
                        Task { await startTiming(selectedMode) }
                    }
                    Button(action: dismiss) {
                        Text("Not now")
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            .frame(maxWidth: .infinity, minHeight: 42)
                    }
                    .buttonStyle(.bordered)
                }
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 26)
            .background(Color(parallax: .cardLight))
            .clipShape(RoundedRectangle(cornerRadius: 26))
            .ignoresSafeArea(edges: .bottom)
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
