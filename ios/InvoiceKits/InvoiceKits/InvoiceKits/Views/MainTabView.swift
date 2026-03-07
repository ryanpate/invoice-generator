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
            InvoiceListView()
                .tabItem {
                    Label("Invoices", systemImage: "list.bullet")
                }
                .tag(Tab.invoices)

            // MARK: Time Tracking
            TimeEntryListView()
                .tabItem {
                    Label("Time", systemImage: "timer")
                }
                .tag(Tab.time)

            // MARK: Dashboard
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "chart.bar")
                }
                .tag(Tab.dashboard)

            // MARK: Settings
            SettingsView()
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
