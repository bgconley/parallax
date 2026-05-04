// DesignTokens.swift
// Generated reference tokens for [APP_NAME]. Final app name TBD.
// These values should be reviewed by design before production.

import SwiftUI

enum AppDesignTokens {
    enum ColorToken {
        static let canvasLight = Color(hex: "F7F4EE")
        static let cardLight = Color(hex: "FFFDF8")
        static let textPrimaryLight = Color(hex: "171717")
        static let textSecondaryLight = Color(hex: "5F5A51")
        static let accentPrimary = Color(hex: "315E8A")
        static let accentSage = Color(hex: "6E8B75")
        static let accentAmber = Color(hex: "B58134")
        static let accentRose = Color(hex: "B26868")
    }

    enum Radius {
        static let chip: CGFloat = 14
        static let button: CGFloat = 16
        static let cardMedium: CGFloat = 20
        static let cardLarge: CGFloat = 26
        static let sheet: CGFloat = 28
    }

    enum Spacing {
        static let xxs: CGFloat = 4
        static let xs: CGFloat = 8
        static let sm: CGFloat = 12
        static let md: CGFloat = 16
        static let lg: CGFloat = 20
        static let xl: CGFloat = 24
        static let xxl: CGFloat = 32
        static let screenHorizontal: CGFloat = 20
        static let cardInner: CGFloat = 16
    }
}

extension Color {
    init(hex: String) {
        let scanner = Scanner(string: hex)
        var value: UInt64 = 0
        scanner.scanHexInt64(&value)
        let r = Double((value >> 16) & 0xFF) / 255.0
        let g = Double((value >> 8) & 0xFF) / 255.0
        let b = Double(value & 0xFF) / 255.0
        self.init(red: r, green: g, blue: b)
    }
}
