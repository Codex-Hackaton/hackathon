import PenaltyDomain
import SwiftUI

struct SplashView: View {
    let onComplete: () -> Void

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [OFFMateTheme.background, Color(hex: 0xEDE8FB), OFFMateTheme.background],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()
            VStack(spacing: 15) {
                JamiMascot(mood: .happy, size: 116)
                Text("OFFMate")
                    .font(.system(size: 43, weight: .black, design: .rounded))
                    .foregroundStyle(OFFMateTheme.text)
                Text("내가 만든 규칙을, 친구와 함께.")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(OFFMateTheme.textSecondary)
                HStack(spacing: 6) {
                    ForEach(0..<3) { _ in Circle().fill(OFFMateTheme.primary).frame(width: 6, height: 6) }
                }
                .padding(.top, 20)
            }
        }
        .task {
            try? await Task.sleep(nanoseconds: 1_600_000_000)
            onComplete()
        }
    }
}

struct OnboardingView: View {
    let onNext: () -> Void

    private let features = [
        ("timer", "통합 숏폼 타이머", "Instagram · YouTube · TikTok 이용 시간을 한 번에 관리해요.", OFFMateTheme.primary),
        ("person.2.fill", "친구의 20분 권한", "이용 시간이 끝난 뒤 선정된 친구가 패널티를 고를 수 있어요.", OFFMateTheme.accent),
        ("camera.fill", "AI 활동 인증", "현실 활동 사진 한 장을 분석해 패널티 해제를 판단해요.", OFFMateTheme.success),
    ]

    var body: some View {
        VStack(spacing: 0) {
            ScrollView(showsIndicators: false) {
                VStack(spacing: 22) {
                    JamiMascot(mood: .happy, size: 100)
                    VStack(spacing: 7) {
                        Text("안녕, 나는 잠이야 👋")
                            .font(.system(size: 27, weight: .black, design: .rounded))
                            .foregroundStyle(OFFMateTheme.text)
                        Text("숏폼 대신 진짜 하고 싶은 일을\n친구와 함께 지킬 수 있게 도와줄게.")
                            .font(.system(size: 14))
                            .foregroundStyle(OFFMateTheme.textSecondary)
                            .multilineTextAlignment(.center)
                            .lineSpacing(5)
                    }
                    VStack(spacing: 10) {
                        ForEach(features, id: \.1) { feature in
                            HStack(spacing: 14) {
                                Image(systemName: feature.0)
                                    .font(.system(size: 20, weight: .bold))
                                    .foregroundStyle(feature.3)
                                    .frame(width: 48, height: 48)
                                    .background(feature.3.opacity(0.10), in: RoundedRectangle(cornerRadius: 15))
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(feature.1)
                                        .font(.system(size: 14, weight: .bold, design: .rounded))
                                        .foregroundStyle(OFFMateTheme.text)
                                    Text(feature.2)
                                        .font(.system(size: 11))
                                        .foregroundStyle(OFFMateTheme.textSecondary)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                                Spacer(minLength: 0)
                            }
                            .offMateCard(padding: 15)
                        }
                    }
                }
                .padding(.horizontal, 22)
                .padding(.top, 32)
                .padding(.bottom, 22)
            }
            VStack(spacing: 10) {
                PrimaryButton(title: "규칙 정하러 가기", icon: "arrow.right", action: onNext)
                Text("잠이가 옆에서 도와줄게!")
                    .font(.system(size: 11))
                    .foregroundStyle(OFFMateTheme.textSecondary)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
    }
}

struct SetupView: View {
    @Binding var dailyLimit: Int
    @Binding var selectedPenalty: PenaltyType
    let onComplete: () -> Void

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 28) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("초기 설정")
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .tracking(1.2)
                        .foregroundStyle(OFFMateTheme.primaryLight)
                    Text("규칙을 정해볼게요.")
                        .font(.system(size: 26, weight: .black, design: .rounded))
                        .foregroundStyle(OFFMateTheme.text)
                    Text("이용 시간이 끝나면 선택한 기본 패널티가 즉시 적용돼요.")
                        .font(.system(size: 12))
                        .foregroundStyle(OFFMateTheme.textSecondary)
                }

                VStack(alignment: .leading, spacing: 13) {
                    SectionTitle(title: "숏폼 이용 가능 시간", required: true)
                    HStack {
                        VStack(alignment: .leading, spacing: 5) {
                            Text("세션당 이용 시간")
                                .font(.system(size: 11))
                                .foregroundStyle(OFFMateTheme.textSecondary)
                            Text("\(dailyLimit)분")
                                .font(.system(size: 27, weight: .black, design: .rounded))
                                .foregroundStyle(OFFMateTheme.text)
                        }
                        Spacer()
                        Picker("이용 시간", selection: $dailyLimit) {
                            Text("20분").tag(20)
                            Text("40분").tag(40)
                        }
                        .labelsHidden()
                        .pickerStyle(.segmented)
                        .frame(width: 150)
                    }
                    .offMateCard()
                }

                VStack(alignment: .leading, spacing: 13) {
                    SectionTitle(title: "기본 패널티", required: true)
                    Text("친구가 20분 안에 다른 패널티를 선택하지 않으면 이 설정이 유지돼요.")
                        .font(.system(size: 11))
                        .foregroundStyle(OFFMateTheme.textSecondary)
                    VStack(spacing: 9) {
                        ForEach(PenaltyType.allCases, id: \.rawValue) { type in
                            PenaltyOptionRow(type: type, selected: selectedPenalty == type) { selectedPenalty = type }
                        }
                    }
                }

                VStack(alignment: .leading, spacing: 12) {
                    SectionTitle(title: "적용 대상 앱", required: true)
                    HStack(spacing: 8) {
                        TargetAppBadge(name: "Instagram", color: Color(hex: 0xE1306C))
                        TargetAppBadge(name: "YouTube", color: OFFMateTheme.danger)
                        TargetAppBadge(name: "TikTok", color: OFFMateTheme.text)
                    }
                    Text("iOS에서 다른 앱 위에 방해물을 겹칠 수 없어 실제 기기에서는 커스텀 shield로 막고, 방해물·흑백·음소거 효과는 OFFMate 데모에서 보여줘요.")
                        .font(.system(size: 10))
                        .foregroundStyle(OFFMateTheme.textSecondary)
                        .lineSpacing(3)
                }

                PrimaryButton(title: "설정 완료, 시작하기", icon: "arrow.right", action: onComplete)
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 28)
        }
        .background(OFFMateTheme.background)
    }
}

struct ScreenHeader: View {
    let title: String
    let onBack: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Button(action: onBack) {
                Image(systemName: "chevron.left")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(OFFMateTheme.textSecondary)
                    .frame(width: 36, height: 36)
                    .background(OFFMateTheme.card, in: RoundedRectangle(cornerRadius: 11))
            }
            .buttonStyle(.plain)
            Text(title)
                .font(.system(size: 18, weight: .black, design: .rounded))
                .foregroundStyle(OFFMateTheme.text)
            Spacer()
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
    }
}

struct ScreenTitle: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.system(size: 25, weight: .black, design: .rounded))
                .foregroundStyle(OFFMateTheme.text)
            Text(subtitle)
                .font(.system(size: 11))
                .foregroundStyle(OFFMateTheme.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 24)
        .padding(.vertical, 18)
    }
}

struct SectionTitle: View {
    let title: String
    let required: Bool

    var body: some View {
        HStack(spacing: 8) {
            Capsule()
                .fill(LinearGradient(colors: [OFFMateTheme.primary, OFFMateTheme.primaryLight], startPoint: .top, endPoint: .bottom))
                .frame(width: 3, height: 18)
            Text(title)
                .font(.system(size: 15, weight: .black, design: .rounded))
                .foregroundStyle(OFFMateTheme.text)
            if required { Text("*").foregroundStyle(OFFMateTheme.danger) }
        }
    }
}

struct TargetAppBadge: View {
    let name: String
    let color: Color

    var body: some View {
        Text(name)
            .font(.system(size: 10, weight: .bold, design: .rounded))
            .foregroundStyle(color)
            .padding(.horizontal, 9)
            .padding(.vertical, 8)
            .background(color.opacity(0.08), in: RoundedRectangle(cornerRadius: 10))
            .overlay { RoundedRectangle(cornerRadius: 10).stroke(color.opacity(0.20)) }
    }
}
