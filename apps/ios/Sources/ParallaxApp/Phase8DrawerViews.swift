import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

struct Phase8DrawerOverlay<Content: View>: View {
    let figmaSheetHeight: CGFloat
    let dismiss: () -> Void
    @ViewBuilder let content: (_ scale: CGFloat) -> Content

    private let figmaWidth: CGFloat = 461

    var body: some View {
        GeometryReader { proxy in
            let scale = proxy.size.width / figmaWidth
            let height = min(figmaSheetHeight * scale, proxy.size.height - 72)

            ZStack(alignment: .bottom) {
                Color.black.opacity(0.24)
                    .ignoresSafeArea()
                    .onTapGesture(perform: dismiss)

                ZStack(alignment: .topLeading) {
                    Capsule()
                        .fill(Color(hex: "#CFC7BD"))
                        .frame(width: 46 * scale, height: 5 * scale)
                        .position(x: figmaWidth * scale / 2, y: 14.5 * scale)
                    content(scale)
                }
                .frame(width: proxy.size.width, height: height, alignment: .topLeading)
                .background(Color(parallax: .cardLight))
                .clipShape(
                    UnevenRoundedRectangle(
                        topLeadingRadius: 28 * scale,
                        bottomLeadingRadius: 0,
                        bottomTrailingRadius: 0,
                        topTrailingRadius: 28 * scale
                    )
                )
                .shadow(color: .black.opacity(0.18), radius: 26 * scale, y: -10 * scale)
            }
            .ignoresSafeArea(edges: .bottom)
        }
    }
}

struct StepDetailDrawerView: View {
    let perform: (Phase8DrawerAction) -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 563, dismiss: {}) { scale in
            drawerText("Step 2 of 6 · running 12:14", x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .active), scale: scale)
            drawerText("Load dishwasher", x: 24, y: 58, w: 413, h: 34, size: 25, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText("Usually 6-12 min. Checkpoint labels stay optional; this step can still teach timing.", x: 24, y: 94, w: 413, h: 42, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)
            accentCard(
                title: "What this step is showing",
                lines: ["Active work 9:48 · elapsed 12:14", "Setup time 0:56 · 1 interruption", "Count policy: active + wall are separate"],
                x: 24, y: 148, w: 413, h: 116, accent: Color(parallax: .active), scale: scale
            )
            drawerChip("often sticky", x: 24, y: 286, w: 104, h: 32, role: .active, scale: scale)
            drawerChip("setup-heavy", x: 140, y: 286, w: 112, h: 32, role: .detour, scale: scale)
            drawerChip("moveable", x: 264, y: 286, w: 98, h: 32, role: .checkpoint, scale: scale)
            drawerButton("Done with this step", x: 24, y: 330, w: 413, h: 50, primary: true, scale: scale) { perform(.completeStep) }
            drawerButton("Pause", x: 24, y: 392, w: 92, h: 42, scale: scale) { perform(.pauseStep) }
            drawerButton("Skip", x: 128, y: 392, w: 92, h: 42, scale: scale) { perform(.skipStep) }
            drawerButton("Move", x: 232, y: 392, w: 92, h: 42, scale: scale) { perform(.moveStep) }
            drawerButton("Note", x: 336, y: 392, w: 92, h: 42, scale: scale) { perform(.addStepNote) }
            accentCard(
                title: "Next: Hand-wash pans",
                lines: ["Predicted 5-14 min · often expands when tools are missing"],
                x: 24, y: 448, w: 413, h: 74, accent: Color(parallax: .checkpoint), scale: scale
            )
        }
    }
}

struct FrictionEvidenceDrawerView: View {
    let perform: (Phase8DrawerAction) -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 573, dismiss: {}) { scale in
            drawerText("Needs confirmation · confidence 0.82", x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .detourText), scale: scale)
            drawerText("Couldn’t find something", x: 24, y: 58, w: 413, h: 34, size: 24, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText("“The sponge is gross. I need to go downstairs and get a new one.”", x: 24, y: 94, w: 413, h: 42, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)
            accentCard(
                title: "Extracted as resource detour",
                lines: ["Resource: sponge · location: downstairs", "Counts as wall time only, not active work", "Suggested check: sponge or scrubber before starting"],
                x: 24, y: 148, w: 413, h: 118, accent: Color(parallax: .detour), scale: scale
            )
            drawerChip("resource", x: 24, y: 283, w: 88, h: 32, role: .detour, scale: scale)
            drawerChip("preflight candidate", x: 122, y: 283, w: 154, h: 32, role: .active, scale: scale)
            drawerChip("wall only", x: 286, y: 283, w: 92, h: 32, role: .interruption, scale: scale)
            accentCard(
                title: "Learning effect",
                lines: ["Repeated confirmed detours can become a preflight check."],
                x: 24, y: 326, w: 413, h: 76, accent: Color(parallax: .active), scale: scale
            )
            drawerButton("Confirm evidence", x: 24, y: 420, w: 413, h: 50, primary: true, scale: scale) { perform(.confirmFrictionEvidence) }
            drawerButton("Correct", x: 24, y: 482, w: 126, h: 42, scale: scale) { perform(.correctFrictionEvidence) }
            drawerButton("Not relevant", x: 162, y: 482, w: 126, h: 42, scale: scale) { perform(.ignoreFrictionEvidence) }
            drawerButton("Keep note only", x: 300, y: 482, w: 128, h: 42, scale: scale) { perform(.keepFrictionNoteOnly) }
        }
    }
}

struct ForgottenTimerDrawerView: View {
    let perform: (Phase8DrawerAction) -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 539, dismiss: {}) { scale in
            drawerText("Review flag · possible forgotten timer", x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .interruptionText), scale: scale)
            drawerText("Did the timer keep running?", x: 24, y: 58, w: 413, h: 34, size: 24, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText("This run may have continued after you left the place where it started. No raw coordinates are shown here.", x: 24, y: 94, w: 413, h: 48, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)
            accentCard(
                title: "What changed",
                lines: ["Idle gap: 45 min", "Started near kitchen · finished near store", "Context quality 0.76 · confidence 0.82"],
                x: 24, y: 154, w: 413, h: 116, accent: Color(parallax: .interruption), scale: scale
            )
            drawerChip("human explanation", x: 24, y: 284, w: 156, h: 32, role: .interruption, scale: scale)
            drawerChip("no raw location", x: 190, y: 284, w: 126, h: 32, role: .wall, scale: scale)
            drawerChip("needs choice", x: 326, y: 284, w: 108, h: 32, role: .checkpoint, scale: scale)
            drawerButton("Trim at place change", x: 24, y: 330, w: 413, h: 48, primary: true, scale: scale) { perform(.trimForgottenTimer) }
            drawerButton("Timer kept running", x: 24, y: 390, w: 413, h: 42, scale: scale) { perform(.timerKeptRunning) }
            drawerButton("Discard timing, keep note", x: 24, y: 444, w: 198, h: 42, scale: scale) { perform(.discardTimingKeepNote) }
            drawerButton("Not sure", x: 234, y: 444, w: 194, h: 42, scale: scale) { perform(.forgottenTimerNotSure) }
        }
    }
}

struct ReviewDecisionDrawerView: View {
    let selectedDecision: ModelUpdateDecision
    let saveDecision: (ModelUpdateDecision) -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 584, dismiss: {}) { scale in
            drawerText("Learning gate · choose what this run teaches", x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .checkpointText), scale: scale)
            drawerText("What should this run update?", x: 24, y: 58, w: 413, h: 34, size: 24, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText("This controls model inclusion. The note can still be kept even when timing is excluded.", x: 24, y: 94, w: 413, h: 42, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)

            ForEach(Array(ReviewDecisionDisplayFactory.options(selected: selectedDecision).enumerated()), id: \.offset) { index, option in
                let y = CGFloat(148 + (index * 66))
                drawerOption(
                    title: option.title,
                    subtitle: option.subtitle,
                    selected: option.selected,
                    x: 24, y: y, w: 413, h: 58, scale: scale
                ) {
                    saveDecision(option.decision)
                }
            }
            drawerButton("Save selected decision", x: 24, y: 490, w: 413, h: 50, primary: true, scale: scale) {
                saveDecision(selectedDecision)
            }
        }
    }
}

struct PreflightEvidenceDrawerView: View {
    let perform: (Phase8DrawerAction) -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 593, dismiss: {}) { scale in
            drawerText("Activity profile · resource dependency", x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .detourText), scale: scale)
            drawerText("Check sponge or scrubber before starting.", x: 24, y: 58, w: 413, h: 60, size: 23, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText("Suggested after 3 confirmed sponge detours across 6 reviewed runs.", x: 24, y: 126, w: 413, h: 38, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)
            accentCard(
                title: "Why I am suggesting this",
                lines: ["Source: resource dependency", "Failure count 3 · confidence 0.81", "Most recent evidence counted as wall-only detour"],
                x: 24, y: 176, w: 413, h: 112, accent: Color(parallax: .detour), scale: scale
            )
            drawerChip("active", x: 24, y: 302, w: 72, h: 28, role: .detour, scale: scale)
            drawerChip("snoozeable", x: 104, y: 302, w: 100, h: 28, role: .interruption, scale: scale)
            drawerChip("hideable", x: 212, y: 302, w: 88, h: 28, role: .wall, scale: scale)
            drawerChip("retire later", x: 308, y: 302, w: 104, h: 28, role: .checkpoint, scale: scale)
            accentCard(
                title: "Last matching note",
                lines: ["“The sponge is gross... go downstairs and get a new one.”"],
                x: 24, y: 348, w: 413, h: 74, accent: Color(parallax: .active), scale: scale
            )
            drawerButton("Keep active", x: 24, y: 440, w: 198, h: 48, primary: true, scale: scale) { perform(.keepPreflightActive) }
            drawerButton("Snooze", x: 234, y: 440, w: 194, h: 48, scale: scale) { perform(.snoozePreflight) }
            drawerButton("Hide", x: 24, y: 500, w: 126, h: 42, scale: scale) { perform(.hidePreflight) }
            drawerButton("Retire", x: 162, y: 500, w: 126, h: 42, scale: scale) { perform(.retirePreflight) }
            drawerButton("View runs", x: 300, y: 500, w: 128, h: 42, scale: scale) { perform(.viewPreflightRuns) }
        }
    }
}

struct CheckpointSetupDrawerView: View {
    let perform: (Phase8DrawerAction) -> Void

    var body: some View {
        Phase8DrawerOverlay(figmaSheetHeight: 589, dismiss: {}) { scale in
            drawerText("Checkpoint setup · Break It Down pattern", x: 24, y: 36, w: 413, h: 18, size: 12, weight: .semibold, color: Color(parallax: .checkpointText), scale: scale)
            drawerText("Hand-wash pans", x: 24, y: 58, w: 413, h: 34, size: 24, weight: .bold, color: Color(parallax: .textPrimaryLight), scale: scale)
            drawerText("Often expands. Keep it as one checkpoint, split it, or make it optional before the run starts.", x: 24, y: 94, w: 413, h: 42, size: 14, weight: .regular, color: Color(parallax: .textSecondaryLight), scale: scale)
            accentCard(
                title: "Current setup",
                lines: ["Predicted 5-14 min · step 3 of 6", "Context: sponge/scrubber issues change this step"],
                x: 24, y: 148, w: 413, h: 96, accent: Color(parallax: .checkpoint), scale: scale
            )
            drawerChip("often expands", x: 24, y: 258, w: 112, h: 28, role: .checkpoint, scale: scale)
            drawerChip("resource-sensitive", x: 144, y: 258, w: 136, h: 28, role: .detour, scale: scale)
            drawerChip("optional label", x: 288, y: 258, w: 112, h: 28, role: .wall, scale: scale)
            drawerOption(title: "Split into smaller steps", subtitle: "rinse · scrub · final rinse", selected: true, x: 24, y: 304, w: 413, h: 58, scale: scale) { perform(.updateCheckpointPlan) }
            drawerOption(title: "Make this checkpoint optional", subtitle: "skip without corrupting sequence", selected: false, x: 24, y: 370, w: 413, h: 58, scale: scale) { perform(.makeCheckpointOptional) }
            drawerOption(title: "Start from this step", subtitle: "begin timing at the selected phase", selected: false, x: 24, y: 436, w: 413, h: 58, scale: scale) { perform(.startFromCheckpoint) }
            drawerButton("Update checkpoint plan", x: 24, y: 512, w: 413, h: 50, primary: true, scale: scale) { perform(.updateCheckpointPlan) }
        }
    }
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
        Text(title)
            .font(.system(size: 14 * scale, weight: .semibold, design: .rounded))
            .lineLimit(1)
            .minimumScaleFactor(0.72)
            .foregroundStyle(primary ? Color.white : Color(parallax: .activeText))
            .frame(width: w * scale, height: h * scale)
            .background(primary ? Color(parallax: .active) : Color(parallax: .cardLight))
            .overlay(
                RoundedRectangle(cornerRadius: 16 * scale)
                    .stroke(primary ? Color.clear : Color(parallax: .separatorLight), lineWidth: max(1, scale))
            )
            .clipShape(RoundedRectangle(cornerRadius: 16 * scale))
    }
    .buttonStyle(.plain)
    .position(x: (x + w / 2) * scale, y: (y + h / 2) * scale)
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
