import PenaltyDomain
import SwiftUI

struct HomeView: View {
    let dailyLimit: Int
    let selectedPenalty: PenaltyType
    let serviceConnected: Bool
    let onControllerDemo: () -> Void
    let onPenaltyDemo: () -> Void
    let onTab: (OFFMateTab) -> Void

    private var usedMinutes: Int { dailyLimit == 40 ? 32 : 16 }
    private var progress: Double { Double(usedMinutes) / Double(dailyLimit) }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("안녕하세요")
                        .font(.system(size: 12))
                        .foregroundStyle(OFFMateTheme.textSecondary)
                    Text("가영 👋")
                        .font(.system(size: 22, weight: .black, design: .rounded))
                        .foregroundStyle(OFFMateTheme.text)
                }
                Spacer()
                Text(serviceConnected ? "API LIVE" : "OFFLINE")
                    .font(.system(size: 9, weight: .black, design: .rounded))
                    .foregroundStyle(serviceConnected ? OFFMateTheme.success : OFFMateTheme.textSecondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 5)
                    .background(
                        (serviceConnected ? OFFMateTheme.success : OFFMateTheme.border).opacity(0.10),
                        in: Capsule()
                    )
                Image(systemName: "bell.fill")
                    .foregroundStyle(OFFMateTheme.textSecondary)
                    .frame(width: 40, height: 40)
                    .background(OFFMateTheme.card, in: RoundedRectangle(cornerRadius: 12))
                    .overlay(alignment: .topTrailing) {
                        Circle().fill(OFFMateTheme.danger).frame(width: 7, height: 7).offset(x: -7, y: 7)
                    }
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 17)

            ScrollView(showsIndicators: false) {
                VStack(spacing: 15) {
                    usageCard
                    demoActions
                    friendCard
                    activityCard
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 24)
            }
            OFFMateBottomBar(selected: .home, onSelect: onTab)
        }
    }

    private var usageCard: some View {
        VStack(spacing: 17) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 5) {
                    Text("오늘의 숏폼 사용")
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .foregroundStyle(OFFMateTheme.primaryLight)
                    HStack(alignment: .firstTextBaseline, spacing: 4) {
                        Text("\(usedMinutes)")
                            .font(.system(size: 38, weight: .black, design: .rounded))
                            .foregroundStyle(OFFMateTheme.accent)
                        Text("/ \(dailyLimit)분")
                            .font(.system(size: 17, weight: .semibold, design: .rounded))
                            .foregroundStyle(OFFMateTheme.textSecondary)
                    }
                }
                Spacer()
                CircularUsageProgress(progress: progress, tint: OFFMateTheme.accent, label: "\(Int(progress * 100))%")
            }
            ProgressView(value: progress).tint(OFFMateTheme.accent)
            HStack {
                Text("남은 시간 \(dailyLimit - usedMinutes)분")
                Spacer()
                Label("사용 가능", systemImage: "circle.fill").foregroundStyle(OFFMateTheme.success)
            }
            .font(.system(size: 11, weight: .medium))
            .foregroundStyle(OFFMateTheme.textSecondary)
        }
        .padding(19)
        .background(
            LinearGradient(colors: [Color(hex: 0xEDE8FB), .white], startPoint: .topLeading, endPoint: .bottomTrailing),
            in: RoundedRectangle(cornerRadius: 20, style: .continuous)
        )
        .overlay { RoundedRectangle(cornerRadius: 20).stroke(OFFMateTheme.primary.opacity(0.20)) }
    }

    private var demoActions: some View {
        VStack(spacing: 9) {
            Button(action: onPenaltyDemo) {
                HStack(spacing: 12) {
                    Image(systemName: "hourglass.bottomhalf.filled").font(.system(size: 20, weight: .bold))
                    VStack(alignment: .leading, spacing: 2) {
                        Text("YouTube 시청 데모").font(.system(size: 13, weight: .bold, design: .rounded))
                        Text("시간 종료 → 친구 패널티 → AI 인증")
                            .font(.system(size: 10)).foregroundStyle(Color.white.opacity(0.68))
                    }
                    Spacer()
                    Image(systemName: "arrow.right")
                }
                .foregroundStyle(.white)
                .padding(15)
                .background(
                    LinearGradient(colors: [OFFMateTheme.text, Color(hex: 0x533483)], startPoint: .leading, endPoint: .trailing),
                    in: RoundedRectangle(cornerRadius: 15)
                )
            }
            .buttonStyle(.plain)

            Button(action: onControllerDemo) {
                HStack {
                    Label("친구 B 화면 보기", systemImage: "person.badge.key.fill")
                    Spacer()
                    Text("20분 권한")
                }
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(OFFMateTheme.primary)
                .padding(14)
                .background(OFFMateTheme.primary.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
                .overlay { RoundedRectangle(cornerRadius: 14).stroke(OFFMateTheme.primary.opacity(0.22)) }
            }
            .buttonStyle(.plain)
        }
    }

    private var friendCard: some View {
        VStack(alignment: .leading, spacing: 13) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("갓생팟").font(.system(size: 14, weight: .bold, design: .rounded)).foregroundStyle(OFFMateTheme.text)
                    Text("멤버 4명").font(.system(size: 11)).foregroundStyle(OFFMateTheme.textSecondary)
                }
                Spacer()
                Text("오늘의 제어자 · 민지")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(OFFMateTheme.primary)
                    .padding(.horizontal, 9).padding(.vertical, 6)
                    .background(OFFMateTheme.primary.opacity(0.09), in: Capsule())
            }
            HStack(spacing: -7) {
                ForEach(Array(["가", "민", "수", "지"].enumerated()), id: \.offset) { index, initial in
                    Text(initial)
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                        .frame(width: 35, height: 35)
                        .background([OFFMateTheme.primary, OFFMateTheme.success, OFFMateTheme.accent, OFFMateTheme.danger][index], in: Circle())
                        .overlay(Circle().stroke(.white, lineWidth: 2))
                }
                Spacer()
                Text("활동 상태만 공유").font(.system(size: 10)).foregroundStyle(OFFMateTheme.textSecondary)
            }
        }
        .offMateCard()
    }

    private var activityCard: some View {
        HStack(spacing: 13) {
            JamiMascot(mood: .happy, size: 45)
            VStack(alignment: .leading, spacing: 4) {
                Text("잠이의 안내").font(.system(size: 12, weight: .bold)).foregroundStyle(OFFMateTheme.success)
                Text("기본 패널티: \(selectedPenalty.offMateTitle)")
                    .font(.system(size: 13, weight: .semibold, design: .rounded)).foregroundStyle(OFFMateTheme.text)
                Text("활동 사진은 제출마다 1장만 받아요.")
                    .font(.system(size: 10)).foregroundStyle(OFFMateTheme.textSecondary)
            }
            Spacer()
        }
        .padding(15)
        .background(OFFMateTheme.success.opacity(0.07), in: RoundedRectangle(cornerRadius: 17))
        .overlay { RoundedRectangle(cornerRadius: 17).stroke(OFFMateTheme.success.opacity(0.18)) }
    }
}
