import SwiftUI

struct SettingsView: View {
    @Environment(AppState.self) private var appState
    @State private var showSignOutConfirm = false

    var body: some View {
        NavigationStack {
            List {
                // MARK: - App Sections
                Section {
                    NavigationLink {
                        CompanyProfileView()
                    } label: {
                        Label("Company Profile", systemImage: "building.2")
                    }

                    NavigationLink {
                        ReminderSettingsView()
                    } label: {
                        Label("Payment Reminders", systemImage: "bell")
                    }

                    NavigationLink {
                        LateFeeSettingsView()
                    } label: {
                        Label("Late Fees", systemImage: "dollarsign.circle")
                    }
                }

                Section {
                    NavigationLink {
                        SubscriptionView()
                    } label: {
                        Label("Subscription & Billing", systemImage: "creditcard")
                    }
                }

                Section {
                    NavigationLink {
                        AppSettingsView()
                    } label: {
                        Label("App Settings", systemImage: "gear")
                    }

                    NavigationLink {
                        AccountView()
                    } label: {
                        Label("Account", systemImage: "person.circle")
                    }
                }

                // MARK: - Sign Out
                Section {
                    Button(role: .destructive) {
                        showSignOutConfirm = true
                    } label: {
                        HStack {
                            Spacer()
                            Text("Sign Out")
                                .fontWeight(.medium)
                            Spacer()
                        }
                    }
                }
            }
            .navigationTitle("Settings")
            .alert("Sign Out", isPresented: $showSignOutConfirm) {
                Button("Sign Out", role: .destructive) {
                    appState.auth.logout()
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Are you sure you want to sign out?")
            }
        }
    }
}

// MARK: - Preview

#Preview {
    SettingsView()
        .environment(AppState())
}
