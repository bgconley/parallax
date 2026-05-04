import SwiftUI

public enum ParallaxDesignTokens {
    public static let version = "1.3"
    public static let appName = "Parallax"

    public enum ColorToken: String, CaseIterable, Codable, Sendable {
        case canvasLight
        case cardLight
        case elevatedLight
        case separatorLight
        case textPrimaryLight
        case textSecondaryLight
        case textTertiaryLight
        case active
        case activeSoft
        case activeText
        case wall
        case wallText
        case checkpoint
        case checkpointSoft
        case checkpointText
        case detour
        case detourSoft
        case detourText
        case interruption
        case interruptionSoft
        case interruptionText
        case waiting
        case waitingSoft
        case waitingText
        case privacy
        case privacyText

        public var hex: String {
            switch self {
            case .canvasLight: "#F6F2EC"
            case .cardLight: "#FFFCF7"
            case .elevatedLight: "#FFFFFF"
            case .separatorLight: "#E7E0D7"
            case .textPrimaryLight: "#181817"
            case .textSecondaryLight: "#5F5A54"
            case .textTertiaryLight: "#8E877D"
            case .active: "#4C7EE8"
            case .activeSoft: "#E7EEFF"
            case .activeText: "#315FC4"
            case .wall: "#D8E3FF"
            case .wallText: "#315FC4"
            case .checkpoint: "#9B84E8"
            case .checkpointSoft: "#F0EAFF"
            case .checkpointText: "#5D45B8"
            case .detour: "#809662"
            case .detourSoft: "#EDF3E5"
            case .detourText: "#506D3D"
            case .interruption: "#C58C3A"
            case .interruptionSoft: "#F8EEDC"
            case .interruptionText: "#835615"
            case .waiting: "#5B8B84"
            case .waitingSoft: "#E6F1EE"
            case .waitingText: "#356E66"
            case .privacy: "#5B8B84"
            case .privacyText: "#356E66"
            }
        }
    }

    public enum Spacing {
        public static let xxs: CGFloat = 4
        public static let xs: CGFloat = 8
        public static let sm: CGFloat = 12
        public static let md: CGFloat = 16
        public static let lg: CGFloat = 20
        public static let xl: CGFloat = 24
        public static let xxl: CGFloat = 32
        public static let screenHorizontal: CGFloat = 20
        public static let screenVertical: CGFloat = 24
        public static let cardInner: CGFloat = 16
        public static let sectionGap: CGFloat = 20
    }

    public enum Radius {
        public static let chip: CGFloat = 16
        public static let button: CGFloat = 18
        public static let cardMedium: CGFloat = 22
        public static let cardLarge: CGFloat = 28
        public static let sheet: CGFloat = 28
        public static let field: CGFloat = 18
    }

    public enum Accessibility {
        public static let minimumTouchTarget: CGFloat = 44
        public static let preferredTouchTarget: CGFloat = 48
        public static let maxDefaultModeChoices = 3
        public static let colorOnlyStatesAllowed = false
        public static let dynamicTypeRequired = true
    }
}

public extension Color {
    init(parallax token: ParallaxDesignTokens.ColorToken) {
        self.init(hex: token.hex)
    }

    init(hex: String) {
        let sanitized = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        var value: UInt64 = 0
        Scanner(string: sanitized).scanHexInt64(&value)
        let red = Double((value >> 16) & 0xFF) / 255.0
        let green = Double((value >> 8) & 0xFF) / 255.0
        let blue = Double(value & 0xFF) / 255.0
        self.init(red: red, green: green, blue: blue)
    }
}
