import PenaltyDomain
import SwiftUI

enum DemoScreen {
    case splash, onboarding, setup, home, viewing, controller, penalty, proof, result
    case group, records, settings
}

enum ProofSample: String, CaseIterable {
    case reading = "책 읽기"
    case gaming = "게임"
    case unclear = "불명확"

    var icon: String {
        switch self {
        case .reading: "book.fill"
        case .gaming: "gamecontroller.fill"
        case .unclear: "questionmark"
        }
    }

    var decision: AIAnalysisDecision {
        switch self {
        case .reading: .pass
        case .gaming: .fail
        case .unclear: .humanReview
        }
    }
}

struct MCPDashboardView: View {
    @StateObject private var liveSession = LiveSessionModel()
    @State private var screen: DemoScreen = .splash
    @State private var selectedPenalty: PenaltyType = .block
    @State private var dailyLimit = 40
    @State private var proofSample: ProofSample?

    var body: some View {
        ZStack {
            OFFMateTheme.background.ignoresSafeArea()
            currentScreen
        }
        .frame(maxWidth: 430, maxHeight: .infinity)
        .preferredColorScheme(.light)
        .animation(.easeInOut(duration: 0.22), value: screen)
        .overlay {
            if liveSession.isLoading {
                ZStack {
                    Color.black.opacity(0.16).ignoresSafeArea()
                    ProgressView("서버와 동기화 중…")
                        .padding(20)
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
                }
            }
        }
        .alert(
            "API 연결 오류",
            isPresented: Binding(
                get: { liveSession.errorMessage != nil },
                set: { if !$0 { liveSession.errorMessage = nil } }
            )
        ) {
            Button("확인", role: .cancel) { liveSession.errorMessage = nil }
        } message: {
            Text(liveSession.errorMessage ?? "알 수 없는 오류")
        }
    }

    @ViewBuilder
    private var currentScreen: some View {
        switch screen {
        case .splash:
            SplashView { screen = .onboarding }
        case .onboarding:
            OnboardingView { screen = .setup }
        case .setup:
            SetupView(dailyLimit: $dailyLimit, selectedPenalty: $selectedPenalty) {
                Task {
                    if await liveSession.prepareSession(defaultPenalty: selectedPenalty) {
                        screen = .home
                    }
                }
            }
        case .home:
            HomeView(
                dailyLimit: dailyLimit,
                selectedPenalty: selectedPenalty,
                serviceConnected: liveSession.isConnected,
                onControllerDemo: { screen = .controller },
                onPenaltyDemo: {
                    Task {
                        if await liveSession.prepareSession(defaultPenalty: selectedPenalty) {
                            screen = .viewing
                        }
                    }
                },
                onTab: showTab
            )
        case .viewing:
            ViewingSessionView(
                configuredMinutes: dailyLimit,
                onExpired: {
                    if await liveSession.endViewing() {
                        screen = .controller
                    }
                },
                onBack: { screen = .home }
            )
        case .controller:
            ControllerView(
                selectedPenalty: $selectedPenalty,
                onApply: {
                    Task {
                        if await liveSession.selectPenalty(selectedPenalty) { screen = .penalty }
                    }
                },
                onBack: { screen = .home }
            )
        case .penalty:
            PenaltyActiveView(
                penalty: selectedPenalty,
                onProof: { proofSample = nil; screen = .proof },
                onController: { screen = .controller },
                onBack: { screen = .home }
            )
        case .proof:
            ProofSubmissionView(
                sample: $proofSample,
                onAnalyze: { imageData in
                    Task {
                        let succeeded: Bool
                        if let imageData {
                            succeeded = await liveSession.submitAndAnalyze(
                                imageData: imageData,
                                contentType: "image/jpeg"
                            )
                        } else if let proofSample {
                            succeeded = await liveSession.submitAndAnalyze(sample: proofSample)
                        } else {
                            return
                        }
                        if succeeded {
                            screen = .result
                        }
                    }
                },
                onBack: { screen = .penalty }
            )
        case .result:
            AIResultView(
                analysis: liveSession.analysis,
                fallbackDecision: proofSample?.decision ?? .humanReview,
                onHome: { screen = .home },
                onRetry: { proofSample = nil; screen = .proof },
                onReview: { passed in
                    await liveSession.resolveHumanReview(passed: passed)
                }
            )
        case .group:
            GroupView(onTab: showTab)
        case .records:
            RecordsView(onTab: showTab)
        case .settings:
            SettingsView(dailyLimit: $dailyLimit, selectedPenalty: $selectedPenalty, onTab: showTab)
        }
    }

    private func showTab(_ tab: OFFMateTab) {
        switch tab {
        case .home: screen = .home
        case .group: screen = .group
        case .records: screen = .records
        case .settings: screen = .settings
        }
    }
}
