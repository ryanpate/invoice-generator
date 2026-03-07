import SwiftUI
import SwiftData

@main
struct InvoiceKitsApp: App {
    @State private var appState = AppState()

    var sharedModelContainer: ModelContainer = {
        let schema = Schema([
            CachedInvoice.self,
            CachedTimeEntry.self,
            CachedCompany.self,
            CachedUserProfile.self,
        ])
        let modelConfiguration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
        do {
            return try ModelContainer(for: schema, configurations: [modelConfiguration])
        } catch {
            fatalError("Could not create ModelContainer: \(error)")
        }
    }()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(appState)
                .modelContainer(sharedModelContainer)
        }
    }
}

// MARK: - Root routing view

private struct RootView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        Group {
            if !appState.auth.isLoggedIn {
                SignInView()
            } else if appState.isFaceIDEnabled && !appState.isUnlocked {
                LockScreenView()
            } else {
                MainTabView()
            }
        }
        .animation(.easeInOut(duration: 0.3), value: appState.auth.isLoggedIn)
        .animation(.easeInOut(duration: 0.3), value: appState.isUnlocked)
    }
}
