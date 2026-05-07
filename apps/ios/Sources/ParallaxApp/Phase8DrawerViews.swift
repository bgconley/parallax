import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

struct Phase8DrawerOverlay<Content: View>: View {
    let figmaSheetHeight: CGFloat
    let dismiss: () -> Void
    @ViewBuilder let content: (_ scale: CGFloat) -> Content

    private let figmaWidth: CGFloat = 461
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    var body: some View {
        GeometryReader { proxy in
            let scale = proxy.size.width / figmaWidth
            let baseHeight = figmaSheetHeight * scale
            let maxHeight = proxy.size.height - (dynamicTypeSize.isAccessibilitySize ? 24 : 72)
            let preferredHeight = dynamicTypeSize.isAccessibilitySize
                ? max(baseHeight, proxy.size.height * 0.82)
                : baseHeight
            let height = min(preferredHeight, maxHeight)

            ZStack(alignment: .bottom) {
                Color.black.opacity(0.24)
                    .ignoresSafeArea()
                    .onTapGesture(perform: dismiss)

                ZStack(alignment: .topLeading) {
                    Capsule()
                        .fill(Color(hex: "#CFC7BD"))
                        .frame(
                            width: ParallaxBottomSheetLayout.handleWidth * scale,
                            height: ParallaxBottomSheetLayout.handleHeight * scale
                        )
                        .position(x: figmaWidth * scale / 2, y: 14.5 * scale)
                    Button(action: dismiss) {
                        Image(systemName: "xmark")
                            .font(.system(size: 14 * scale, weight: .bold))
                            .foregroundStyle(Color(parallax: .textSecondaryLight))
                            .frame(width: 34 * scale, height: 34 * scale)
                            .background(Color(parallax: .elevatedLight))
                            .clipShape(Circle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Close")
                    .position(x: proxy.size.width - 34 * scale, y: 31 * scale)
                    content(scale)
                }
                .frame(width: proxy.size.width, height: height, alignment: .topLeading)
                .parallaxBottomAttachedSheet(
                    topCornerRadius: 28 * scale,
                    fill: Color(parallax: .cardLight),
                    shadowOpacity: 0.16,
                    shadowRadius: 24 * scale,
                    shadowY: -8 * scale
                )
            }
            .ignoresSafeArea(edges: .bottom)
        }
    }
}

struct StepDetailDrawerView: View {
    let detail: StepDetailProjection
    let perform: (Phase8DrawerAction) -> Void
    let dismiss: () -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 563, dismiss: dismiss) { scale in
            drawerText(detail.eyebrow, x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .active), scale: scale)
            drawerText(detail.title, x: 24, y: 58, w: 413, h: 34, size: 25, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText(detail.subtitle, x: 24, y: 94, w: 413, h: 42, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)
            accentCard(
                title: detail.summaryTitle,
                lines: detail.summaryLines,
                x: 24, y: 148, w: 413, h: 116, accent: Color(parallax: .active), scale: scale
            )
            drawerChip(detail.chips[safe: 0] ?? "no run", x: 24, y: 286, w: 104, h: 32, role: .active, scale: scale)
            drawerChip(detail.chips[safe: 1] ?? "no change", x: 140, y: 286, w: 112, h: 32, role: .detour, scale: scale)
            drawerChip(detail.chips[safe: 2] ?? "canonical", x: 264, y: 286, w: 98, h: 32, role: .checkpoint, scale: scale)
            drawerButton("Complete checkpoint", x: 24, y: 330, w: 413, h: 50, primary: true, scale: scale) { perform(.completeStep) }
                .disabled(!detail.canCompleteStep)
            drawerButton("Pause", x: 24, y: 392, w: 92, h: 42, scale: scale) { perform(.pauseStep) }
                .disabled(!detail.canPause)
            drawerButton("Skip", x: 128, y: 392, w: 92, h: 42, scale: scale) { perform(.skipStep) }
                .disabled(!detail.canSkip)
            drawerButton("Move", x: 232, y: 392, w: 92, h: 42, scale: scale) { perform(.moveStep) }
                .disabled(!detail.canMove)
            drawerButton("Note", x: 336, y: 392, w: 92, h: 42, scale: scale) { perform(.addStepNote) }
                .disabled(!detail.canAddNote)
            accentCard(
                title: detail.nextTitle,
                lines: detail.nextLines,
                x: 24, y: 448, w: 413, h: 74, accent: Color(parallax: .checkpoint), scale: scale
            )
        }
    }
}

struct FrictionEvidenceDrawerView: View {
    let evidence: FrictionEvidenceProjection
    let perform: (Phase8DrawerAction) -> Void
    let dismiss: () -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 573, dismiss: dismiss) { scale in
            drawerText(evidence.eyebrow, x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .detourText), scale: scale)
            drawerText(evidence.title, x: 24, y: 58, w: 413, h: 34, size: 24, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText(evidence.subtitle, x: 24, y: 94, w: 413, h: 42, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)
            accentCard(
                title: evidence.evidenceTitle,
                lines: evidence.evidenceLines,
                x: 24, y: 148, w: 413, h: 118, accent: Color(parallax: .detour), scale: scale
            )
            drawerChip(evidence.chips[safe: 0] ?? "no evidence", x: 24, y: 283, w: 104, h: 32, role: .detour, scale: scale)
            drawerChip(evidence.chips[safe: 1] ?? "no change", x: 140, y: 283, w: 104, h: 32, role: .active, scale: scale)
            drawerChip(evidence.chips[safe: 2] ?? "log first", x: 256, y: 283, w: 122, h: 32, role: .interruption, scale: scale)
            accentCard(
                title: evidence.learningTitle,
                lines: evidence.learningLines,
                x: 24, y: 326, w: 413, h: 76, accent: Color(parallax: .active), scale: scale
            )
            drawerButton("Confirm evidence", x: 24, y: 420, w: 413, h: 50, primary: true, scale: scale) { perform(.confirmFrictionEvidence) }
                .disabled(!evidence.canConfirm)
            drawerButton("Correct", x: 24, y: 482, w: 126, h: 42, scale: scale) { perform(.correctFrictionEvidence) }
                .disabled(!evidence.canCorrect)
            drawerButton("Not relevant", x: 162, y: 482, w: 126, h: 42, scale: scale) { perform(.ignoreFrictionEvidence) }
                .disabled(!evidence.canIgnore)
            drawerButton("Keep note only", x: 300, y: 482, w: 128, h: 42, scale: scale) { perform(.keepFrictionNoteOnly) }
                .disabled(!evidence.canKeepNoteOnly)
        }
    }
}

struct ForgottenTimerDrawerView: View {
    let evidence: ForgottenTimerEvidenceProjection
    let perform: (Phase8DrawerAction) -> Void
    let dismiss: () -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 593, dismiss: dismiss) { scale in
            drawerText(evidence.eyebrow, x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .interruptionText), scale: scale)
            drawerText(evidence.title, x: 24, y: 58, w: 413, h: 34, size: 24, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText(evidence.subtitle, x: 24, y: 94, w: 413, h: 48, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)
            accentCard(
                title: evidence.evidenceTitle,
                lines: evidence.evidenceLines,
                x: 24, y: 154, w: 413, h: 116, accent: Color(parallax: .interruption), scale: scale
            )
            drawerChip(evidence.chips[safe: 0] ?? "no flag", x: 24, y: 284, w: 156, h: 32, role: .interruption, scale: scale)
            drawerChip(evidence.chips[safe: 1] ?? "no change", x: 190, y: 284, w: 126, h: 32, role: .wall, scale: scale)
            drawerChip(evidence.chips[safe: 2] ?? "safe", x: 326, y: 284, w: 108, h: 32, role: .checkpoint, scale: scale)
            drawerButton("Trim at place change", x: 24, y: 330, w: 413, h: 48, primary: true, scale: scale) { perform(.trimForgottenTimer) }
                .disabled(!evidence.canTrim)
            drawerButton("Timer kept running", x: 24, y: 390, w: 413, h: 42, scale: scale) { perform(.timerKeptRunning) }
                .disabled(!evidence.canResolveKeptRunning)
            drawerButton("Discard timing, keep note", x: 24, y: 444, w: 413, h: 42, scale: scale) { perform(.discardTimingKeepNote) }
            drawerButton("Not sure", x: 24, y: 498, w: 413, h: 42, scale: scale) { perform(.forgottenTimerNotSure) }
                .disabled(!evidence.canDefer)
        }
    }
}

struct ReviewDecisionDrawerView: View {
    let selectedDecision: ModelUpdateDecision
    let saveDecision: (ModelUpdateDecision) -> Void
    let dismiss: () -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 746, dismiss: dismiss) { scale in
            drawerText("Learning gate · choose what this run teaches", x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .checkpointText), scale: scale)
            drawerText("What should this run update?", x: 24, y: 58, w: 413, h: 34, size: 24, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText("This controls model inclusion. The note can still be kept even when timing is excluded.", x: 24, y: 94, w: 413, h: 42, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)

            ForEach(Array(ReviewDecisionDisplayFactory.options(selected: selectedDecision).enumerated()), id: \.offset) { index, option in
                let y = CGFloat(148 + (index * 62))
                drawerOption(
                    title: option.title,
                    subtitle: option.subtitle,
                    selected: option.selected,
                    x: 24, y: y, w: 413, h: 56, scale: scale
                ) {
                    saveDecision(option.decision)
                }
            }
            drawerButton("Save selected decision", x: 24, y: 668, w: 413, h: 50, primary: true, scale: scale) {
                saveDecision(selectedDecision)
            }
        }
    }
}

struct PreflightEvidenceDrawerView: View {
    let evidence: PreflightEvidenceProjection
    let perform: (Phase8DrawerAction) -> Void
    let dismiss: () -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 593, dismiss: dismiss) { scale in
            drawerText("Activity profile · resource dependency", x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .detourText), scale: scale)
            drawerText(evidence.title, x: 24, y: 58, w: 413, h: 60, size: 23, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText(evidence.subtitle, x: 24, y: 126, w: 413, h: 38, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)
            accentCard(
                title: evidence.evidenceTitle,
                lines: evidence.evidenceLines,
                x: 24, y: 176, w: 413, h: 112, accent: Color(parallax: .detour), scale: scale
            )
            preflightChip(index: 0, text: evidence.chips[safe: 0] ?? "no evidence", role: .detour, scale: scale)
            preflightChip(index: 1, text: evidence.chips[safe: 1] ?? "no change", role: .interruption, scale: scale)
            preflightChip(index: 2, text: evidence.chips[safe: 2] ?? "review first", role: .wall, scale: scale)
            preflightChip(index: 3, text: evidence.chips[safe: 3] ?? "canonical", role: .checkpoint, scale: scale)
            accentCard(
                title: evidence.noteTitle,
                lines: evidence.noteLines,
                x: 24, y: 348, w: 413, h: 74, accent: Color(parallax: .active), scale: scale
            )
            drawerButton("Keep active", x: 24, y: 440, w: 198, h: 48, primary: true, scale: scale) { perform(.keepPreflightActive) }
                .disabled(evidence.primaryCheckId == nil)
            drawerButton("Snooze", x: 234, y: 440, w: 194, h: 48, scale: scale) { perform(.snoozePreflight) }
                .disabled(evidence.primaryCheckId == nil)
            drawerButton("Hide", x: 24, y: 500, w: 126, h: 42, scale: scale) { perform(.hidePreflight) }
                .disabled(evidence.primaryCheckId == nil)
            drawerButton("Retire", x: 162, y: 500, w: 126, h: 42, scale: scale) { perform(.retirePreflight) }
                .disabled(evidence.primaryCheckId == nil)
            drawerButton("View runs", x: 300, y: 500, w: 128, h: 42, scale: scale) { perform(.viewPreflightRuns) }
        }
    }
}

struct CheckpointSetupDrawerView: View {
    let perform: (Phase8DrawerAction) -> Void
    let dismiss: () -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 589, dismiss: dismiss) { scale in
            drawerText("Checkpoint timing setup", x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .checkpointText), scale: scale)
            drawerText("Selected checkpoint", x: 24, y: 58, w: 413, h: 34, size: 24, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText("Keep this timing marker, add a phase boundary, or make the checkpoint optional before the run starts.", x: 24, y: 94, w: 413, h: 42, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)
            accentCard(
                title: "Current timing setup",
                lines: ["Prediction appears after reviewed timing samples exist", "Context can explain timing variation"],
                x: 24, y: 148, w: 413, h: 96, accent: Color(parallax: .checkpoint), scale: scale
            )
            drawerChip("can split timing", x: 24, y: 258, w: 112, h: 28, role: .checkpoint, scale: scale)
            drawerChip("resource-sensitive", x: 144, y: 258, w: 136, h: 28, role: .detour, scale: scale)
            drawerChip("optional label", x: 288, y: 258, w: 112, h: 28, role: .wall, scale: scale)
            drawerOption(title: "Add timing checkpoint", subtitle: "separate phase boundary", selected: true, x: 24, y: 304, w: 413, h: 58, scale: scale) { perform(.updateCheckpointPlan) }
            drawerOption(title: "Make this checkpoint optional", subtitle: "skip without corrupting timing order", selected: false, x: 24, y: 370, w: 413, h: 58, scale: scale) { perform(.makeCheckpointOptional) }
            drawerOption(title: "Start at this checkpoint", subtitle: "begin timing at the selected phase", selected: false, x: 24, y: 436, w: 413, h: 58, scale: scale) { perform(.startFromCheckpoint) }
            drawerButton("Update timing checkpoints", x: 24, y: 512, w: 413, h: 50, primary: true, scale: scale) { perform(.updateCheckpointPlan) }
        }
    }
}

private func preflightChip(
    index: Int,
    text: String,
    role: TemporalSemanticRole,
    scale: CGFloat
) -> some View {
    let slots: [(x: CGFloat, w: CGFloat)] = [
        (24, 106),
        (138, 92),
        (238, 82),
        (328, 86),
    ]
    let slot = slots[min(max(index, 0), slots.count - 1)]
    return drawerChip(text, x: slot.x, y: 302, w: slot.w, h: 28, role: role, scale: scale)
}

private func drawerText(
    _ text: String,
    x: CGFloat,
    y: CGFloat,
    w: CGFloat,
    h: CGFloat,
    size: CGFloat,
    weight: Font.Weight,
    color: Color,
    scale: CGFloat
) -> some View {
    Text(text)
        .font(.system(size: size * scale, weight: weight, design: .rounded))
        .lineSpacing(0)
        .foregroundStyle(color)
        .lineLimit(nil)
        .fixedSize(horizontal: false, vertical: true)
        .frame(width: w * scale, height: h * scale, alignment: .topLeading)
        .position(x: (x + w / 2) * scale, y: (y + h / 2) * scale)
}

private extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}

private func accentCard(
    title: String,
    lines: [String],
    x: CGFloat,
    y: CGFloat,
    w: CGFloat,
    h: CGFloat,
    accent: Color,
    scale: CGFloat
) -> some View {
    ZStack(alignment: .topLeading) {
        RoundedRectangle(cornerRadius: 16 * scale)
            .fill(Color.white)
        RoundedRectangle(cornerRadius: 16 * scale)
            .stroke(Color(parallax: .separatorLight), lineWidth: max(1, scale))
        Rectangle()
            .fill(accent)
            .frame(width: 4 * scale, height: h * scale)
        VStack(alignment: .leading, spacing: 7 * scale) {
            Text(title)
                .font(.system(size: 14 * scale, weight: .semibold, design: .rounded))
                .foregroundStyle(Color(parallax: .textPrimaryLight))
            ForEach(lines, id: \.self) { line in
                Text(line)
                    .font(.system(size: 12 * scale, weight: .regular, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
            }
        }
        .padding(.leading, 16 * scale)
        .padding(.top, 14 * scale)
        .padding(.trailing, 16 * scale)
    }
    .frame(width: w * scale, height: h * scale)
    .position(x: (x + w / 2) * scale, y: (y + h / 2) * scale)
}

private func drawerChip(
    _ text: String,
    x: CGFloat,
    y: CGFloat,
    w: CGFloat,
    h: CGFloat,
    role: TemporalSemanticRole,
    scale: CGFloat
) -> some View {
    Text(text)
        .font(.system(size: 12 * scale, weight: .medium, design: .rounded))
        .foregroundStyle(Color(parallax: DesignTokenMapper.colorToken(for: role)))
        .lineLimit(1)
        .minimumScaleFactor(0.75)
        .frame(width: w * scale, height: h * scale)
        .background(Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)))
        .clipShape(Capsule())
        .position(x: (x + w / 2) * scale, y: (y + h / 2) * scale)
}

@MainActor
private func drawerButton(
    _ title: String,
    x: CGFloat,
    y: CGFloat,
    w: CGFloat,
    h: CGFloat,
    primary: Bool = false,
    scale: CGFloat,
    action: @escaping () -> Void
) -> some View {
    Button(action: action) {
        DrawerActionLabel(title: title, primary: primary, scale: scale, width: w * scale, height: h * scale)
    }
    .buttonStyle(.plain)
    .position(x: (x + w / 2) * scale, y: (y + h / 2) * scale)
}

private struct DrawerActionLabel: View {
    let title: String
    let primary: Bool
    let scale: CGFloat
    let width: CGFloat
    let height: CGFloat
    @Environment(\.isEnabled) private var isEnabled

    private var foreground: Color {
        if isEnabled {
            return primary ? .white : Color(parallax: .activeText)
        }
        return Color(parallax: .textSecondaryLight).opacity(ParallaxDrawerActionLayout.disabledLabelOpacity)
    }

    private var fill: Color {
        if primary {
            return isEnabled
                ? Color(parallax: .active)
                : Color(parallax: .separatorLight).opacity(ParallaxDrawerActionLayout.disabledBackgroundOpacity)
        }
        return isEnabled
            ? Color(parallax: .cardLight)
            : Color(parallax: .elevatedLight).opacity(ParallaxDrawerActionLayout.disabledBackgroundOpacity)
    }

    private var stroke: Color {
        primary && isEnabled ? Color.clear : Color(parallax: .separatorLight)
    }

    var body: some View {
        Text(title)
            .font(.system(size: 14 * scale, weight: .semibold, design: .rounded))
            .lineLimit(1)
            .minimumScaleFactor(0.72)
            .foregroundStyle(foreground)
            .frame(width: width, height: height)
            .background(fill)
            .overlay(
                RoundedRectangle(cornerRadius: 16 * scale)
                    .stroke(stroke, lineWidth: max(1, scale))
            )
            .clipShape(RoundedRectangle(cornerRadius: 16 * scale))
    }
}

@MainActor
private func drawerOption(
    title: String,
    subtitle: String,
    selected: Bool,
    x: CGFloat,
    y: CGFloat,
    w: CGFloat,
    h: CGFloat,
    scale: CGFloat,
    action: @escaping () -> Void
) -> some View {
    Button(action: action) {
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 16 * scale)
                .fill(selected ? Color(hex: "#F2F6FF") : Color.white)
            RoundedRectangle(cornerRadius: 16 * scale)
                .stroke(selected ? Color(parallax: .active) : Color(parallax: .separatorLight), lineWidth: max(1, scale))
            Circle()
                .fill(selected ? Color(parallax: .active) : Color(hex: "#F1EDE7"))
                .frame(width: 20 * scale, height: 20 * scale)
                .position(x: 24 * scale, y: 28 * scale)
            VStack(alignment: .leading, spacing: 4 * scale) {
                Text(title)
                    .font(.system(size: 13 * scale, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color(parallax: .textPrimaryLight))
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
                Text(subtitle)
                    .font(.system(size: 11 * scale, weight: .regular, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
            }
            .frame(width: 355 * scale, height: 40 * scale, alignment: .leading)
            .position(x: (44 + 355 / 2) * scale, y: 30 * scale)
        }
        .frame(width: w * scale, height: h * scale)
    }
    .buttonStyle(.plain)
    .position(x: (x + w / 2) * scale, y: (y + h / 2) * scale)
}
