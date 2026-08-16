import PenaltyDomain
import SwiftUI

enum MascotMood {
    case happy
    case worried
    case thinking
    case celebrate
}

struct JamiMascot: View {
    let mood: MascotMood
    var size: CGFloat = 92

    var body: some View {
        ZStack {
            Circle()
                .fill(OFFMateTheme.primary.opacity(0.10))
                .frame(width: size * 1.15, height: size * 1.15)

            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [Color(hex: 0xB99AFF), OFFMateTheme.primaryLight],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )

                HStack(spacing: size * 0.20) {
                    eye
                    eye
                }
                .offset(y: -size * 0.06)

                mouth
                    .offset(y: size * 0.16)

                if mood == .celebrate {
                    Text("✨")
                        .font(.system(size: size * 0.28))
                        .offset(x: size * 0.47, y: -size * 0.35)
                }
            }
            .frame(width: size, height: size)
            .overlay(alignment: .topLeading) {
                Circle()
                    .fill(Color(hex: 0xD9CBFF))
                    .frame(width: size * 0.25, height: size * 0.25)
                    .offset(x: size * 0.08, y: -size * 0.05)
            }
            .overlay(alignment: .topTrailing) {
                Circle()
                    .fill(Color(hex: 0xD9CBFF))
                    .frame(width: size * 0.25, height: size * 0.25)
                    .offset(x: -size * 0.08, y: -size * 0.05)
            }
        }
        .frame(width: size * 1.2, height: size * 1.2)
        .accessibilityLabel("OFFMate 마스코트 잠이")
    }

    private var eye: some View {
        Group {
            switch mood {
            case .happy, .celebrate:
                Capsule()
                    .fill(OFFMateTheme.text)
                    .frame(width: size * 0.07, height: size * 0.12)
            case .worried, .thinking:
                Circle()
                    .fill(OFFMateTheme.text)
                    .frame(width: size * 0.09, height: size * 0.09)
            }
        }
    }

    private var mouth: some View {
        Group {
            switch mood {
            case .happy, .celebrate:
                Image(systemName: "mouth.fill")
                    .font(.system(size: size * 0.18))
                    .foregroundStyle(OFFMateTheme.text)
            case .worried:
                Capsule()
                    .fill(OFFMateTheme.text)
                    .frame(width: size * 0.16, height: size * 0.05)
                    .rotationEffect(.degrees(-8))
            case .thinking:
                Circle()
                    .stroke(OFFMateTheme.text, lineWidth: 2)
                    .frame(width: size * 0.12, height: size * 0.12)
            }
        }
    }
}

struct PrimaryButton: View {
    let title: String
    var icon: String?
    var enabled = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Text(title)
                if let icon {
                    Image(systemName: icon)
                }
            }
            .font(.system(size: 15, weight: .bold, design: .rounded))
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .frame(height: 52)
            .background(
                LinearGradient(
                    colors: enabled
                        ? [OFFMateTheme.primary, OFFMateTheme.primaryLight]
                        : [OFFMateTheme.border, OFFMateTheme.border],
                    startPoint: .leading,
                    endPoint: .trailing
                ),
                in: RoundedRectangle(cornerRadius: 16, style: .continuous)
            )
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
    }
}

struct CircularUsageProgress: View {
    let progress: Double
    let tint: Color
    let label: String

    var body: some View {
        ZStack {
            Circle().stroke(OFFMateTheme.border, lineWidth: 7)
            Circle()
                .trim(from: 0, to: min(max(progress, 0), 1))
                .stroke(tint, style: StrokeStyle(lineWidth: 7, lineCap: .round))
                .rotationEffect(.degrees(-90))
            Text(label)
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(tint)
        }
        .frame(width: 64, height: 64)
        .animation(.easeInOut(duration: 0.35), value: progress)
    }
}

extension PenaltyType {
    var offMateTitle: String {
        switch self {
        case .block: "완전 차단"
        case .grayscale: "흑백 화면"
        case .obstruction: "방해물 화면"
        case .muted: "소리 끄기"
        }
    }

    var offMateSubtitle: String {
        switch self {
        case .block: "선택한 숏폼 앱 전체를 잠가요"
        case .grayscale: "데모 플레이어를 흑백으로 바꿔요"
        case .obstruction: "움직이는 방해물이 화면을 계속 가려요"
        case .muted: "데모 영상의 소리를 꺼요"
        }
    }

    var offMateIcon: String {
        switch self {
        case .block: "lock.fill"
        case .grayscale: "circle.lefthalf.filled"
        case .obstruction: "rectangle.on.rectangle.angled"
        case .muted: "speaker.slash.fill"
        }
    }

    var offMateTint: Color {
        switch self {
        case .block: OFFMateTheme.danger
        case .grayscale: Color(hex: 0x6B7280)
        case .obstruction: OFFMateTheme.accent
        case .muted: OFFMateTheme.primary
        }
    }
}

struct PenaltyOptionRow: View {
    let type: PenaltyType
    let selected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 13) {
                Image(systemName: type.offMateIcon)
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(type.offMateTint)
                    .frame(width: 42, height: 42)
                    .background(type.offMateTint.opacity(0.10), in: RoundedRectangle(cornerRadius: 13))

                VStack(alignment: .leading, spacing: 3) {
                    Text(type.offMateTitle)
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundStyle(selected ? type.offMateTint : OFFMateTheme.text)
                    Text(type.offMateSubtitle)
                        .font(.system(size: 11, weight: .regular))
                        .foregroundStyle(OFFMateTheme.textSecondary)
                }
                Spacer(minLength: 6)
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(selected ? type.offMateTint : OFFMateTheme.border)
            }
            .padding(14)
            .background(
                selected ? type.offMateTint.opacity(0.07) : OFFMateTheme.card,
                in: RoundedRectangle(cornerRadius: 16, style: .continuous)
            )
            .overlay {
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(selected ? type.offMateTint : OFFMateTheme.border, lineWidth: selected ? 1.5 : 1)
            }
        }
        .buttonStyle(.plain)
    }
}

enum OFFMateTab: CaseIterable {
    case home
    case group
    case records
    case settings

    var title: String {
        switch self {
        case .home: "홈"
        case .group: "그룹"
        case .records: "기록"
        case .settings: "설정"
        }
    }

    var icon: String {
        switch self {
        case .home: "house.fill"
        case .group: "person.2.fill"
        case .records: "chart.bar.fill"
        case .settings: "gearshape.fill"
        }
    }
}

struct OFFMateBottomBar: View {
    let selected: OFFMateTab
    let onSelect: (OFFMateTab) -> Void

    var body: some View {
        HStack {
            ForEach(OFFMateTab.allCases, id: \.title) { tab in
                Button {
                    onSelect(tab)
                } label: {
                    VStack(spacing: 5) {
                        Image(systemName: tab.icon)
                            .font(.system(size: 17, weight: .semibold))
                        Text(tab.title)
                            .font(.system(size: 10, weight: .semibold, design: .rounded))
                    }
                    .foregroundStyle(selected == tab ? OFFMateTheme.primary : OFFMateTheme.textSecondary.opacity(0.55))
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.top, 12)
        .padding(.bottom, 14)
        .background(.ultraThinMaterial)
        .overlay(alignment: .top) { Divider().overlay(OFFMateTheme.border) }
    }
}
