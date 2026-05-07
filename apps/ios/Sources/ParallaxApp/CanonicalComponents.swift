import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

public enum ParallaxBottomSheetLayout {
    public static let topCornerRadius: CGFloat = 24
    public static let bottomCornerRadius: CGFloat = 0
    public static let handleWidth: CGFloat = 46
    public static let handleHeight: CGFloat = 5
    public static let precedingContentGap: CGFloat = 26
    public static let bottomContentPadding: CGFloat = 14
    public static let usesFlatBottomShape = true
    public static let usesFloatingCardShape = false
}

public enum ParallaxDrawerActionLayout {
    public static let disabledLabelOpacity: Double = 0.9
    public static let disabledBackgroundOpacity: Double = 0.78
    public static let disabledPrimaryUsesNeutralFill = true
    public static let disabledActionsHideText = false
}

public enum ParallaxStaticRowAccessoryLayout {
    public static let nonInteractiveSummaryRowsShowChevron = false
    public static let nonInteractiveStepRowsShowChevron = false
}

extension View {
    func parallaxBottomAttachedSheet(
        topCornerRadius: CGFloat = ParallaxBottomSheetLayout.topCornerRadius,
        fill: Color = Color(parallax: .elevatedLight).opacity(0.98),
        stroke: Color = Color(parallax: .separatorLight),
        shadowOpacity: Double = 0.08,
        shadowRadius: CGFloat = 14,
        shadowY: CGFloat = -4
    ) -> some View {
        let shape = UnevenRoundedRectangle(
            topLeadingRadius: topCornerRadius,
            bottomLeadingRadius: ParallaxBottomSheetLayout.bottomCornerRadius,
            bottomTrailingRadius: ParallaxBottomSheetLayout.bottomCornerRadius,
            topTrailingRadius: topCornerRadius
        )
        return self
            .background(fill)
            .overlay(shape.stroke(stroke, lineWidth: 1))
            .clipShape(shape)
            .shadow(color: .black.opacity(shadowOpacity), radius: shadowRadius, y: shadowY)
    }
}

struct CanonicalScreen<Content: View>: View {
    let title: String
    let subtitle: String?
    let leadingIcon: String
    let leadingAction: (() -> Void)?
    @ViewBuilder let content: () -> Content

    init(
        title: String,
        subtitle: String?,
        leadingIcon: String,
        leadingAction: (() -> Void)? = nil,
        @ViewBuilder content: @escaping () -> Content
    ) {
        self.title = title
        self.subtitle = subtitle
        self.leadingIcon = leadingIcon
        self.leadingAction = leadingAction
        self.content = content
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 8) {
                header
                content()
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 16)
        }
        .background(Color(parallax: .canvasLight))
    }

    private var header: some View {
        HStack(alignment: .top) {
            if let leadingAction {
                Button(action: leadingAction) {
                    CircleIcon(systemName: leadingIcon)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Back")
            } else {
                CircleIcon(systemName: leadingIcon)
            }
            Spacer()
            VStack(spacing: 3) {
                Text(title)
                    .font(.system(size: 27, weight: .bold, design: .rounded))
                    .multilineTextAlignment(.center)
                    .foregroundStyle(Color(parallax: .textPrimaryLight))
                    .minimumScaleFactor(0.72)
                if let subtitle {
                    Text(subtitle)
                        .font(.system(size: 12.5, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                        .multilineTextAlignment(.center)
                        .lineLimit(3)
                        .minimumScaleFactor(0.82)
                }
            }
            .frame(maxWidth: .infinity)
            Spacer()
            CircleIcon(systemName: "sparkles", tint: Color(parallax: .detourText))
        }
        .padding(.top, 8)
    }
}

struct Card<Content: View>: View {
    let background: Color
    @ViewBuilder let content: () -> Content

    init(background: Color = Color(parallax: .cardLight), @ViewBuilder content: @escaping () -> Content) {
        self.background = background
        self.content = content
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            content()
        }
        .padding(8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(background)
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(Color(parallax: .separatorLight), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.045), radius: 9, y: 3)
    }
}

struct CircleIcon: View {
    let systemName: String
    var tint: Color = Color(parallax: .textSecondaryLight)
    var fill: Color = Color(parallax: .cardLight)
    var size: CGFloat = 36
    var symbolSize: CGFloat = 15

    var body: some View {
        Image(systemName: systemName)
            .font(.system(size: symbolSize, weight: .semibold))
            .foregroundStyle(tint)
            .frame(width: size, height: size)
            .background(fill)
            .clipShape(Circle())
            .overlay(Circle().stroke(Color(parallax: .separatorLight), lineWidth: 1))
    }
}

struct SoftBadge: View {
    let text: String
    let systemName: String?
    var role: TemporalSemanticRole = .active

    var body: some View {
        Label {
            Text(text)
                .lineLimit(1)
                .minimumScaleFactor(0.68)
        } icon: {
            if let systemName {
                Image(systemName: systemName)
            }
        }
        .font(.system(size: 9.2, weight: .semibold, design: .rounded))
        .padding(.horizontal, 6)
        .frame(minHeight: 21)
        .background(Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)))
        .foregroundStyle(Color(parallax: DesignTokenMapper.colorToken(for: role)))
        .clipShape(Capsule())
        .overlay(Capsule().stroke(Color(parallax: .separatorLight).opacity(0.5), lineWidth: 1))
    }
}

struct ActivitySummaryRow: View {
    let title: String
    let subtitle: String
    let detail: String
    let icon: String
    var showsChevron: Bool = ParallaxStaticRowAccessoryLayout.nonInteractiveSummaryRowsShowChevron

    var body: some View {
        Card {
            HStack(spacing: 11) {
                ZStack {
                    Circle()
                        .fill(Color(parallax: .detourSoft))
                    Image(systemName: icon)
                        .font(.system(size: 22, weight: .medium))
                        .foregroundStyle(Color(parallax: .detourText))
                }
                .frame(width: 52, height: 52)

                VStack(alignment: .leading, spacing: 3) {
                    Text(title)
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .foregroundStyle(Color(parallax: .textPrimaryLight))
                        .lineLimit(2)
                        .minimumScaleFactor(0.82)
                    Text(subtitle)
                        .font(.system(size: 10.5, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                        .lineLimit(1)
                        .minimumScaleFactor(0.62)
                    Text(detail)
                        .font(.system(size: 10.5, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                        .lineLimit(1)
                        .minimumScaleFactor(0.62)
                }
                Spacer()
                if showsChevron {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color(parallax: .textTertiaryLight))
                }
            }
        }
    }
}

struct DurationText: View {
    let seconds: Int

    var body: some View {
        Text(formatted)
            .monospacedDigit()
    }

    private var formatted: String {
        let minutes = seconds / 60
        let remainder = seconds % 60
        return "\(minutes):\(String(format: "%02d", remainder))"
    }
}

struct StepRow: View {
    let index: Int
    let title: String
    let estimate: String
    let tag: String
    let status: StepStatus
    var trailingText: String?
    var showsChevron: Bool = ParallaxStaticRowAccessoryLayout.nonInteractiveStepRowsShowChevron

    var body: some View {
        HStack(spacing: 6) {
            ZStack {
                Circle()
                    .fill(status.fill)
                status.icon(index: index)
                    .font(.system(size: 10, weight: .bold, design: .rounded))
                    .foregroundStyle(status.foreground)
            }
            .frame(width: 20, height: 20)

            Text(title)
                .font(.system(size: 10.8, weight: .semibold, design: .rounded))
                .foregroundStyle(Color(parallax: .textPrimaryLight))
                .lineLimit(2)
                .minimumScaleFactor(0.78)
                .frame(maxWidth: .infinity, alignment: .leading)

            Text(estimate)
                .font(.system(size: 8.7, weight: .medium, design: .rounded))
                .foregroundStyle(Color(parallax: .textSecondaryLight))
                .lineLimit(1)
                .minimumScaleFactor(0.7)

            Text(tag)
                .font(.system(size: 7.8, weight: .medium, design: .rounded))
                .foregroundStyle(Color(parallax: .detourText))
                .lineLimit(1)
                .minimumScaleFactor(0.6)
                .padding(.horizontal, 5)
                .padding(.vertical, 1)
                .background(Color(parallax: .detourSoft))
                .clipShape(Capsule())

            Spacer()
            Text(trailingText ?? status.trailingText)
                .font(.system(size: 8.7, weight: .medium, design: .rounded))
                .foregroundStyle(status == .running ? Color(parallax: .active) : Color(parallax: .textSecondaryLight))
                .lineLimit(1)
                .minimumScaleFactor(0.65)
            if showsChevron {
                Image(systemName: "chevron.right")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(Color(parallax: .textTertiaryLight))
            }
        }
        .padding(.vertical, 2)
        .padding(.horizontal, 6)
        .background(status == .running ? Color(parallax: .activeSoft).opacity(0.45) : Color.clear)
        .overlay(
            RoundedRectangle(cornerRadius: 9)
                .stroke(status == .running ? Color(parallax: .active) : Color.clear, lineWidth: 1.2)
        )
        .clipShape(RoundedRectangle(cornerRadius: 9))
    }
}

enum StepStatus {
    case done
    case running
    case pending

    var fill: Color {
        switch self {
        case .done: Color(parallax: .detour)
        case .running: Color(parallax: .active)
        case .pending: Color(parallax: .separatorLight)
        }
    }

    var foreground: Color {
        switch self {
        case .done, .running: .white
        case .pending: Color(parallax: .textSecondaryLight)
        }
    }

    @ViewBuilder
    func icon(index: Int) -> some View {
        switch self {
        case .done:
            Image(systemName: "checkmark")
        case .running:
            Text("\(index)")
        case .pending:
            Text("\(index)")
        }
    }

    var trailingText: String {
        switch self {
        case .done:
            return "Done"
        case .running:
            return "Running"
        case .pending:
            return ""
        }
    }
}

struct PrimaryButton: View {
    let title: String
    let systemName: String?
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label {
                Text(title)
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
            } icon: {
                if let systemName {
                    Image(systemName: systemName)
                }
            }
            .frame(maxWidth: .infinity, minHeight: 36)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
    }
}
