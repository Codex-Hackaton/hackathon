import PenaltyDomain
import PhotosUI
import SwiftUI
import UIKit

struct ViewingSessionView: View {
    let configuredMinutes: Int
    let onExpired: () async -> Void
    let onBack: () -> Void

    @State private var remainingDemoSeconds = 8
    @State private var didExpire = false

    var body: some View {
        VStack(spacing: 0) {
            ScreenHeader(title: "YouTube 시청 중", onBack: onBack)
            ScrollView(showsIndicators: false) {
                VStack(spacing: 18) {
                    VStack(spacing: 5) {
                        Text("설정한 \(configuredMinutes)분 이용 세션")
                            .font(.system(size: 12, weight: .bold, design: .rounded))
                            .foregroundStyle(OFFMateTheme.primary)
                        Text("종료까지 \(remainingDemoSeconds)초")
                            .font(.system(size: 28, weight: .black, design: .rounded))
                            .foregroundStyle(remainingDemoSeconds <= 3 ? OFFMateTheme.danger : OFFMateTheme.text)
                        Text("시연에서는 설정 시간을 8초로 축약해 보여줘요.")
                            .font(.system(size: 10))
                            .foregroundStyle(OFFMateTheme.textSecondary)
                    }

                    ZStack(alignment: .bottom) {
                        LinearGradient(
                            colors: [Color(hex: 0x17151F), Color(hex: 0x5B527A)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                        VStack(spacing: 14) {
                            Image(systemName: "play.rectangle.fill")
                                .font(.system(size: 52, weight: .bold))
                            Text("YouTube Shorts")
                                .font(.system(size: 18, weight: .black, design: .rounded))
                            Text("외부 앱 화면은 개인정보 보호를 위해\nOFFMate에 전달되지 않아요.")
                                .font(.system(size: 11))
                                .multilineTextAlignment(.center)
                                .foregroundStyle(.white.opacity(0.68))
                        }
                        .foregroundStyle(.white)

                        ProgressView(value: Double(8 - remainingDemoSeconds), total: 8)
                            .tint(OFFMateTheme.accent)
                            .padding(16)
                    }
                    .frame(height: 390)
                    .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))

                    VStack(spacing: 9) {
                        Label("시간이 끝나면 기본 패널티가 즉시 적용돼요.", systemImage: "hourglass.bottomhalf.filled")
                        Label("선정된 친구는 20분 동안 패널티를 바꿀 수 있어요.", systemImage: "person.badge.key.fill")
                    }
                    .font(.system(size: 11, weight: .semibold, design: .rounded))
                    .foregroundStyle(OFFMateTheme.textSecondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .offMateCard()

                    Button("종료 시점으로 바로 이동") {
                        expireNow()
                    }
                    .buttonStyle(.plain)
                    .font(.system(size: 12, weight: .bold, design: .rounded))
                    .foregroundStyle(OFFMateTheme.primary)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 30)
            }
        }
        .task {
            while remainingDemoSeconds > 0 && !Task.isCancelled {
                try? await Task.sleep(for: .seconds(1))
                guard !Task.isCancelled else { return }
                remainingDemoSeconds -= 1
            }
            if remainingDemoSeconds == 0 {
                await expire()
            }
        }
    }

    private func expireNow() {
        remainingDemoSeconds = 0
        Task { await expire() }
    }

    @MainActor
    private func expire() async {
        guard !didExpire else { return }
        didExpire = true
        await onExpired()
    }
}

struct ControllerView: View {
    @Binding var selectedPenalty: PenaltyType
    let onApply: () -> Void
    let onBack: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            ScreenHeader(title: "친구 B · 패널티 선택", onBack: onBack)
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 20) {
                    HStack(spacing: 13) {
                        Text("민")
                            .font(.system(size: 18, weight: .black, design: .rounded))
                            .foregroundStyle(.white)
                            .frame(width: 48, height: 48)
                            .background(OFFMateTheme.primary, in: Circle())
                        VStack(alignment: .leading, spacing: 3) {
                            Text("민지님이 무작위로 선정됐어요")
                                .font(.system(size: 14, weight: .bold, design: .rounded))
                                .foregroundStyle(OFFMateTheme.text)
                            Text("가영의 사용 기록과 화면 내용은 보이지 않아요.")
                                .font(.system(size: 10))
                                .foregroundStyle(OFFMateTheme.textSecondary)
                        }
                    }
                    .offMateCard()

                    HStack {
                        Label("Penalty Window", systemImage: "timer")
                        Spacer()
                        Text("20:00").font(.system(size: 23, weight: .black, design: .rounded))
                    }
                    .font(.system(size: 12, weight: .bold, design: .rounded))
                    .foregroundStyle(OFFMateTheme.accent)
                    .padding(16)
                    .background(OFFMateTheme.accent.opacity(0.09), in: RoundedRectangle(cornerRadius: 16))

                    VStack(alignment: .leading, spacing: 11) {
                        SectionTitle(title: "적용할 패널티", required: true)
                        Text("아무것도 선택하지 않으면 가영이 미리 정한 기본 패널티가 유지돼요.")
                            .font(.system(size: 10))
                            .foregroundStyle(OFFMateTheme.textSecondary)
                        ForEach(PenaltyType.allCases, id: \.rawValue) { type in
                            PenaltyOptionRow(type: type, selected: selectedPenalty == type) { selectedPenalty = type }
                        }
                    }
                    PrimaryButton(title: "\(selectedPenalty.offMateTitle) 적용", icon: "bolt.fill", action: onApply)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 30)
            }
        }
    }
}

struct PenaltyActiveView: View {
    let penalty: PenaltyType
    let onProof: () -> Void
    let onController: () -> Void
    let onBack: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            ScreenHeader(title: "패널티 적용 중", onBack: onBack)
            ScrollView(showsIndicators: false) {
                VStack(spacing: 22) {
                    JamiMascot(mood: .worried, size: 94)
                    VStack(spacing: 6) {
                        Text("오늘 이용 시간이 끝났어요")
                            .font(.system(size: 24, weight: .black, design: .rounded))
                            .foregroundStyle(OFFMateTheme.text)
                        Text("기본 패널티가 즉시 적용됐어요.")
                            .font(.system(size: 13))
                            .foregroundStyle(OFFMateTheme.textSecondary)
                    }
                    VStack(spacing: 15) {
                        Image(systemName: penalty.offMateIcon)
                            .font(.system(size: 28, weight: .bold))
                            .foregroundStyle(penalty.offMateTint)
                            .frame(width: 64, height: 64)
                            .background(penalty.offMateTint.opacity(0.10), in: Circle())
                        Text(penalty.offMateTitle)
                            .font(.system(size: 20, weight: .black, design: .rounded))
                            .foregroundStyle(penalty.offMateTint)
                        Text(penalty.rawValue)
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundStyle(OFFMateTheme.textSecondary)
                        Text(penalty.offMateSubtitle)
                            .font(.system(size: 12))
                            .foregroundStyle(OFFMateTheme.textSecondary)
                    }
                    .frame(maxWidth: .infinity)
                    .offMateCard()

                    if penalty == .obstruction {
                        ObstructionPenaltyPreview()
                    }

                    VStack(spacing: 10) {
                        statusRow(icon: "person.fill", title: "선정된 친구", value: "민지")
                        Divider().overlay(OFFMateTheme.border)
                        statusRow(icon: "timer", title: "친구 선택 권한", value: "20분")
                        Divider().overlay(OFFMateTheme.border)
                        statusRow(icon: "camera.fill", title: "해제 조건", value: "활동 사진 PASS")
                    }
                    .offMateCard()

                    PrimaryButton(title: "활동 사진 1장 제출", icon: "camera.fill", action: onProof)
                    Button("친구 B 화면에서 변경해보기", action: onController)
                        .buttonStyle(.plain)
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(OFFMateTheme.primary)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 30)
            }
        }
    }

    private func statusRow(icon: String, title: String, value: String) -> some View {
        HStack {
            Label(title, systemImage: icon).foregroundStyle(OFFMateTheme.textSecondary)
            Spacer()
            Text(value).foregroundStyle(OFFMateTheme.text)
        }
        .font(.system(size: 12, weight: .semibold, design: .rounded))
    }
}

private struct ObstructionPenaltyPreview: View {
    @State private var shifted = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("방해물 패널티 미리보기", systemImage: "eye.slash.fill")
                Spacer()
                Text("DEMO")
                    .font(.system(size: 9, weight: .black, design: .rounded))
                    .padding(.horizontal, 7)
                    .padding(.vertical, 4)
                    .background(OFFMateTheme.accent.opacity(0.12), in: Capsule())
            }
            .font(.system(size: 12, weight: .bold, design: .rounded))
            .foregroundStyle(OFFMateTheme.text)

            ZStack {
                LinearGradient(
                    colors: [Color(hex: 0x24213B), Color(hex: 0x665B91)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                VStack(spacing: 8) {
                    Image(systemName: "play.rectangle.fill")
                        .font(.system(size: 28))
                    Text("Reels 영상 영역")
                        .font(.system(size: 11, weight: .semibold, design: .rounded))
                }
                .foregroundStyle(.white.opacity(0.74))

                RoundedRectangle(cornerRadius: 13)
                    .fill(OFFMateTheme.accent.opacity(0.96))
                    .frame(width: shifted ? 180 : 112, height: 52)
                    .overlay {
                        Label("잠깐 쉬어가기", systemImage: "hand.raised.fill")
                            .font(.system(size: 11, weight: .black, design: .rounded))
                            .foregroundStyle(.white)
                    }
                    .offset(x: shifted ? -45 : 48, y: shifted ? 28 : -25)

                Circle()
                    .fill(OFFMateTheme.primaryLight.opacity(0.96))
                    .frame(width: 62, height: 62)
                    .overlay(Image(systemName: "sparkles").foregroundStyle(.white))
                    .offset(x: shifted ? 82 : -88, y: shifted ? -38 : 36)
            }
            .frame(height: 150)
            .clipShape(RoundedRectangle(cornerRadius: 17, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 17, style: .continuous)
                    .stroke(OFFMateTheme.accent.opacity(0.22))
            }

            Text("실제 iPhone에서는 선택 앱의 커스텀 shield로 전환됩니다.")
                .font(.system(size: 10))
                .foregroundStyle(OFFMateTheme.textSecondary)
        }
        .offMateCard()
        .task {
            withAnimation(.easeInOut(duration: 1.2).repeatForever(autoreverses: true)) {
                shifted = true
            }
        }
    }
}

struct ProofSubmissionView: View {
    @Binding var sample: ProofSample?
    let onAnalyze: (Data?) -> Void
    let onBack: () -> Void
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedPhotoData: Data?

    var body: some View {
        VStack(spacing: 0) {
            ScreenHeader(title: "현실 활동 인증", onBack: onBack)
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(spacing: 7) {
                        JamiMascot(mood: .thinking, size: 72)
                        Text("사진 한 장을 확인할게요")
                            .font(.system(size: 21, weight: .black, design: .rounded))
                            .foregroundStyle(OFFMateTheme.text)
                        Text("얼굴 인식이나 신원 추정은 하지 않아요.")
                            .font(.system(size: 11))
                            .foregroundStyle(OFFMateTheme.textSecondary)
                    }
                    .frame(maxWidth: .infinity)

                    VStack(spacing: 12) {
                        Image(systemName: selectedPhotoData != nil ? "photo.fill" : sample?.icon ?? "camera.fill")
                            .font(.system(size: 31, weight: .bold))
                            .foregroundStyle(hasSelection ? OFFMateTheme.success : OFFMateTheme.primary)
                        Text(selectionTitle)
                            .font(.system(size: 14, weight: .bold, design: .rounded))
                            .foregroundStyle(OFFMateTheme.text)
                        Text("한 제출에는 사진을 한 장만 첨부할 수 있어요.")
                            .font(.system(size: 10))
                            .foregroundStyle(OFFMateTheme.textSecondary)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 150)
                    .background(OFFMateTheme.surface, in: RoundedRectangle(cornerRadius: 18))
                    .overlay {
                        RoundedRectangle(cornerRadius: 18)
                            .stroke(hasSelection ? OFFMateTheme.success : OFFMateTheme.border, style: StrokeStyle(lineWidth: 2, dash: [7]))
                    }

                    PhotosPicker(selection: $selectedPhoto, matching: .images) {
                        Label("사진 보관함에서 1장 선택", systemImage: "photo.on.rectangle")
                            .font(.system(size: 13, weight: .bold, design: .rounded))
                            .foregroundStyle(OFFMateTheme.primary)
                            .frame(maxWidth: .infinity)
                            .frame(height: 46)
                            .background(OFFMateTheme.primary.opacity(0.08), in: RoundedRectangle(cornerRadius: 13))
                            .overlay { RoundedRectangle(cornerRadius: 13).stroke(OFFMateTheme.primary.opacity(0.22)) }
                    }
                    .buttonStyle(.plain)
                    .onChange(of: selectedPhoto) { _, item in
                        Task {
                            let original = try? await item?.loadTransferable(type: Data.self)
                            selectedPhotoData = original.flatMap {
                                UIImage(data: $0)?.jpegData(compressionQuality: 0.85)
                            }
                            if selectedPhotoData != nil { sample = nil }
                        }
                    }

                    VStack(alignment: .leading, spacing: 10) {
                        Text("데모 입력 선택")
                            .font(.system(size: 12, weight: .bold, design: .rounded))
                            .foregroundStyle(OFFMateTheme.text)
                        HStack(spacing: 8) {
                            ForEach(ProofSample.allCases, id: \.rawValue) { item in
                                Button {
                                    sample = item
                                    selectedPhoto = nil
                                    selectedPhotoData = nil
                                } label: {
                                    VStack(spacing: 7) {
                                        Image(systemName: item.icon)
                                        Text(item.rawValue)
                                    }
                                    .font(.system(size: 11, weight: .bold, design: .rounded))
                                    .foregroundStyle(sample == item ? .white : OFFMateTheme.primary)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 66)
                                    .background(sample == item ? OFFMateTheme.primary : OFFMateTheme.primary.opacity(0.08), in: RoundedRectangle(cornerRadius: 13))
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }

                    VStack(spacing: 8) {
                        analysisStep(number: "1", text: "Vision AI가 활동 후보를 추출")
                        analysisStep(number: "2", text: "그룹 정책과 활동을 비교")
                        analysisStep(number: "3", text: "PASS · FAIL · HUMAN_REVIEW 반환")
                    }
                    .offMateCard()
                    PrimaryButton(
                        title: "AI 분석 시작",
                        icon: "sparkles",
                        enabled: hasSelection,
                        action: { onAnalyze(selectedPhotoData) }
                    )
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 30)
            }
        }
    }

    private var hasSelection: Bool {
        sample != nil || selectedPhotoData != nil
    }

    private var selectionTitle: String {
        if selectedPhotoData != nil { return "실제 사진 1장 선택됨" }
        if let sample { return "\(sample.rawValue) 데모 사진 선택됨" }
        return "인증 사진을 선택하세요"
    }

    private func analysisStep(number: String, text: String) -> some View {
        HStack(spacing: 10) {
            Text(number)
                .font(.system(size: 10, weight: .black, design: .rounded))
                .foregroundStyle(.white)
                .frame(width: 21, height: 21)
                .background(OFFMateTheme.primary, in: RoundedRectangle(cornerRadius: 6))
            Text(text).font(.system(size: 11, weight: .medium)).foregroundStyle(OFFMateTheme.textSecondary)
            Spacer()
        }
    }
}

struct AIResultView: View {
    let analysis: AIAnalysis?
    let fallbackDecision: AIAnalysisDecision
    let onHome: () -> Void
    let onRetry: () -> Void
    let onReview: (Bool) async -> Bool
    @State private var reviewerDecision: Bool?

    private var decision: AIAnalysisDecision {
        analysis?.decision ?? fallbackDecision
    }

    private var effectiveDecision: AIAnalysisDecision {
        guard decision == .humanReview, let reviewerDecision else { return decision }
        return reviewerDecision ? .pass : .fail
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: 22) {
                JamiMascot(mood: effectiveDecision == .pass ? .celebrate : .worried, size: 96)
                VStack(spacing: 7) {
                    Text(resultTitle)
                        .font(.system(size: 28, weight: .black, design: .rounded))
                        .foregroundStyle(resultColor)
                    Text(resultSubtitle)
                        .font(.system(size: 13))
                        .foregroundStyle(OFFMateTheme.textSecondary)
                        .multilineTextAlignment(.center)
                        .lineSpacing(4)
                }
                VStack(spacing: 12) {
                    resultRow(label: "decision", value: effectiveDecision.rawValue)
                    Divider().overlay(OFFMateTheme.border)
                    resultRow(label: "decision_confidence", value: confidence)
                    Divider().overlay(OFFMateTheme.border)
                    resultRow(label: "matched_policy_ids", value: policyID)
                    if let evidence = analysis?.detectedActivities.first?.visualEvidence.first {
                        Divider().overlay(OFFMateTheme.border)
                        resultRow(label: "visual_evidence", value: evidence)
                    }
                }
                .offMateCard()

                if decision == .humanReview && reviewerDecision == nil {
                    reviewerPanel
                } else if effectiveDecision == .pass {
                    VStack(spacing: 8) {
                        Label("패널티 해제", systemImage: "lock.open.fill")
                        Text("세션이 완료됐어요.")
                    }
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundStyle(OFFMateTheme.success)
                    .frame(maxWidth: .infinity)
                    .offMateCard()
                    PrimaryButton(title: "홈으로", icon: "house.fill", action: onHome)
                } else {
                    VStack(spacing: 7) {
                        Label("패널티 유지", systemImage: "lock.fill")
                        Text("AI FAIL은 친구가 뒤집을 수 없어요.")
                    }
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(OFFMateTheme.danger)
                    .frame(maxWidth: .infinity)
                    .offMateCard()
                    PrimaryButton(title: "새 인증 제출", icon: "camera.fill", action: onRetry)
                }
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 40)
        }
    }

    private var reviewerPanel: some View {
        VStack(alignment: .leading, spacing: 14) {
            Label("민지의 최종 검토가 필요해요", systemImage: "person.crop.circle.badge.questionmark")
                .font(.system(size: 14, weight: .bold, design: .rounded))
                .foregroundStyle(OFFMateTheme.primary)
            Text("AI 신뢰도가 낮을 때만 무작위로 선정된 친구 한 명이 판단해요.")
                .font(.system(size: 11))
                .foregroundStyle(OFFMateTheme.textSecondary)
            HStack(spacing: 9) {
                Button("FAIL") {
                    Task {
                        if await onReview(false) { reviewerDecision = false }
                    }
                }
                    .buttonStyle(.plain)
                    .foregroundStyle(OFFMateTheme.danger)
                    .frame(maxWidth: .infinity).frame(height: 44)
                    .background(OFFMateTheme.danger.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                Button("PASS") {
                    Task {
                        if await onReview(true) { reviewerDecision = true }
                    }
                }
                    .buttonStyle(.plain)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity).frame(height: 44)
                    .background(OFFMateTheme.success, in: RoundedRectangle(cornerRadius: 12))
            }
            .font(.system(size: 13, weight: .bold, design: .rounded))
        }
        .offMateCard()
    }

    private var resultTitle: String {
        switch effectiveDecision {
        case .pass: "PASS"
        case .fail: "FAIL"
        case .humanReview: "HUMAN REVIEW"
        }
    }

    private var resultSubtitle: String {
        switch effectiveDecision {
        case .pass: "허용된 현실 활동으로 확인됐어요."
        case .fail: "그룹의 집중 목표와 충돌하는 활동이에요."
        case .humanReview: "이미지만으로 확신하기 어려워 친구에게 보냈어요."
        }
    }

    private var resultColor: Color {
        switch effectiveDecision {
        case .pass: OFFMateTheme.success
        case .fail: OFFMateTheme.danger
        case .humanReview: OFFMateTheme.accent
        }
    }

    private var confidence: String {
        if let analysis {
            return String(format: "%.2f", analysis.decisionConfidence)
        }
        return "-"
    }

    private var policyID: String {
        analysis?.matchedPolicyIds.first ?? "pending_review"
    }

    private func resultRow(label: String, value: String) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label)
                .font(.system(size: 10, weight: .medium, design: .monospaced))
                .foregroundStyle(OFFMateTheme.textSecondary)
            Spacer()
            Text(value)
                .font(.system(size: 11, weight: .bold, design: .monospaced))
                .foregroundStyle(OFFMateTheme.text)
        }
    }
}
