import SwiftUI

@main
struct PenaltyDemoApp: App {
    var body: some Scene {
        WindowGroup {
            MCPDashboardView()
#if os(macOS)
                .frame(minWidth: 390, idealWidth: 430, minHeight: 760, idealHeight: 860)
#endif
        }
#if os(macOS)
        .windowResizability(.contentSize)
#endif
    }
}
