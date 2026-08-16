import PenaltyDomain
import SwiftUI

struct GroupView: View {
    let onTab: (OFFMateTab) -> Void

    private let members = [
        ("가영", "활동 중", "book.fill", OFFMateTheme.success),
        ("민지", "Penalty Window", "timer", OFFMateTheme.accent),
        ("수현", "오늘 활동 완료", "checkmark.circle.fill", OFFMateTheme.success),
        ("지민", "패널티 적용 중", "lock.fill", OFFMateTheme.danger),
    ]

    var body: some View {
        VStack(spacing: 0) {
            ScreenTitle(title: "갓생팟", subtitle: "친구의 활동 상태만 확인해요")
            ScrollView(showsIndicators: false) {
                VStack(spacing: 12) {
                    HStack {
                        Label("오늘의 무작위 제어자", systemImage: "dice.fill")
                        Spacer()
                        Text("민지")
                    }
                    .font(.system(size: 12, weight: .bold, design: .rounded))
                    .foregroundStyle(OFFMateTheme.primary)
                    .offMateCard()

                    ForEach(Array(members.enumerated()), id: \.offset) { index, member in
                        HStack(spacing: 13) {
                            Text(String(member.0.prefix(1)))
                                .font(.system(size: 14, weight: .black, design: .rounded))
                                .foregroundStyle(.white)
                                .frame(width: 43, height: 43)
                                .background([OFFMateTheme.primary, OFFMateTheme.success, OFFMateTheme.accent, OFFMateTheme.danger][index], in: Circle())
                            VStack(alignment: .leading, spacing: 4) {
                                Text(member.0)
                                    .font(.system(size: 14, weight: .bold, design: .rounded))
                                    .foregroundStyle(OFFMateTheme.text)
                                Label(member.1, systemImage: member.2)
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundStyle(member.3)
                            }
                            Spacer()
                            Image(systemName: "chevron.right").foregroundStyle(OFFMateTheme.border)
                        }
                        .offMateCard(padding: 15)
                    }

                    Text("숏폼 사용 기록, 화면 내용, DM, 검색 기록은 친구에게 공개하지 않습니다.")
                        .font(.system(size: 10))
                        .foregroundStyle(OFFMateTheme.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.top, 5)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 25)
            }
            OFFMateBottomBar(selected: .group, onSelect: onTab)
        }
    }
}

struct RecordsView: View {
    let onTab: (OFFMateTab) -> Void

    var body: some View {
        VStack(spacing: 0) {
            ScreenTitle(title: "내 기록", subtitle: "내 기기에서 보는 활동 기록")
            ScrollView(showsIndicators: false) {
                VStack(spacing: 13) {
                    HStack(spacing: 10) {
                        metric(value: "3일", label: "연속 달성", tint: OFFMateTheme.accent)
                        metric(value: "80분", label: "현실 활동", tint: OFFMateTheme.primary)
                    }
                    activityRow(icon: "book.fill", title: "알고리즘 과제", detail: "오늘 · 20분", passed: true)
                    activityRow(icon: "figure.run", title: "운동", detail: "어제 · 30분", passed: true)
                    activityRow(icon: "gamecontroller.fill", title: "게임", detail: "8월 14일 · FAIL", passed: false)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 24)
            }
            OFFMateBottomBar(selected: .records, onSelect: onTab)
        }
    }

    private func metric(value: String, label: String, tint: Color) -> some View {
        VStack(spacing: 5) {
            Text(value).font(.system(size: 24, weight: .black, design: .rounded)).foregroundStyle(tint)
            Text(label).font(.system(size: 10)).foregroundStyle(OFFMateTheme.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .offMateCard()
    }

    private func activityRow(icon: String, title: String, detail: String, passed: Bool) -> some View {
        HStack(spacing: 13) {
            Image(systemName: icon)
                .foregroundStyle(passed ? OFFMateTheme.success : OFFMateTheme.danger)
                .frame(width: 42, height: 42)
                .background((passed ? OFFMateTheme.success : OFFMateTheme.danger).opacity(0.09), in: RoundedRectangle(cornerRadius: 12))
            VStack(alignment: .leading, spacing: 3) {
                Text(title).font(.system(size: 13, weight: .bold, design: .rounded)).foregroundStyle(OFFMateTheme.text)
                Text(detail).font(.system(size: 10)).foregroundStyle(OFFMateTheme.textSecondary)
            }
            Spacer()
            Text(passed ? "PASS" : "FAIL")
                .font(.system(size: 10, weight: .black, design: .rounded))
                .foregroundStyle(passed ? OFFMateTheme.success : OFFMateTheme.danger)
        }
        .offMateCard(padding: 15)
    }
}

struct SettingsView: View {
    @Binding var dailyLimit: Int
    @Binding var selectedPenalty: PenaltyType
    let onTab: (OFFMateTab) -> Void

    var body: some View {
        VStack(spacing: 0) {
            ScreenTitle(title: "설정", subtitle: "내가 동의한 규칙만 적용돼요")
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 18) {
                    SectionTitle(title: "이용 시간", required: false)
                    Picker("이용 시간", selection: $dailyLimit) {
                        Text("20분").tag(20)
                        Text("40분").tag(40)
                    }
                    .pickerStyle(.segmented)

                    SectionTitle(title: "기본 패널티", required: false)
                    VStack(spacing: 8) {
                        ForEach(PenaltyType.allCases, id: \.rawValue) { type in
                            PenaltyOptionRow(type: type, selected: selectedPenalty == type) { selectedPenalty = type }
                        }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Label("안전 원칙", systemImage: "hand.raised.fill")
                            .font(.system(size: 13, weight: .bold, design: .rounded))
                            .foregroundStyle(OFFMateTheme.primary)
                        Text("친구는 동의한 세션의 20분 Penalty Window에서만 권한을 가져요. AI는 패널티를 새로 만들거나 직접 해제하지 않아요.")
                            .font(.system(size: 10))
                            .foregroundStyle(OFFMateTheme.textSecondary)
                            .lineSpacing(3)
                    }
                    .offMateCard()
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 24)
            }
            OFFMateBottomBar(selected: .settings, onSelect: onTab)
        }
    }
}
