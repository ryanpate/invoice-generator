import SwiftUI

struct MainTabView: View {
    @Environment(AppState.self) private var appState

    @State private var selectedTab: Tab = .invoices

    // MARK: - Tab definition

    enum Tab: Hashable {
        case invoices
        case time
        case dashboard
        case settings
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            // MARK: Invoices
            NavigationStack {
                Text("Invoices")
                    .navigationTitle("Invoices")
            }
            .tabItem {
                Label("Invoices", systemImage: "list.bullet")
            }
            .tag(Tab.invoices)

            // MARK: Time Tracking
            NavigationStack {
                Text("Time Tracking")
                    .navigationTitle("Time Tracking")
            }
            .tabItem {
                Label("Time", systemImage: "timer")
            }
            .tag(Tab.time)

            // MARK: Dashboard
            NavigationStack {
                Text("Dashboard")
                    .navigationTitle("Dashboard")
            }
            .tabItem {
                Label("Dashboard", systemImage: "chart.bar")
            }
            .tag(Tab.dashboard)

            // MARK: Settings
            NavigationStack {
                Text("Settings")
                    .navigationTitle("Settings")
            }
            .tabItem {
                Label("Settings", systemImage: "gear")
            }
            .tag(Tab.settings)
        }
    }
}

#Preview {
    MainTabView()
        .environment(AppState())
}
