import SwiftUI

enum OFFMateTheme {
    static let background = Color(hex: 0xF8F7FF)
    static let surface = Color(hex: 0xF0EDFB)
    static let card = Color.white
    static let cardSecondary = Color(hex: 0xF5F3FD)
    static let primary = Color(hex: 0x7C3AED)
    static let primaryLight = Color(hex: 0x9F67FF)
    static let accent = Color(hex: 0xF59E0B)
    static let success = Color(hex: 0x059669)
    static let danger = Color(hex: 0xDC2626)
    static let text = Color(hex: 0x1A1230)
    static let textSecondary = Color(hex: 0x7B7899)
    static let border = Color(hex: 0xE4E0F5)
}

extension Color {
    init(hex: UInt32, alpha: Double = 1) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: alpha
        )
    }
}

extension View {
    func offMateCard(padding: CGFloat = 18) -> some View {
        self
            .padding(padding)
            .background(OFFMateTheme.card, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(OFFMateTheme.border, lineWidth: 1)
            }
    }
}
