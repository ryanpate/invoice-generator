import SwiftUI

struct AccountView: View {
    @Environment(AppState.self) private var appState

    @State private var showDeleteStep1 = false
    @State private var showDeleteStep2 = false
    @State private var deleteConfirmationText = ""
    @State private var isDeleting = false
    @State private var errorMessage: String?

    private var currentEmail: String {
        appState.auth.currentUser?.email ?? "—"
    }

    private var deleteConfirmed: Bool {
        deleteConfirmationText == "DELETE"
    }

    var body: some View {
        List {
            accountInfoSection
            dangerZoneSection
        }
        .navigationTitle("Account")
        .navigationBarTitleDisplayMode(.inline)
        // Step 1 — initial confirmation
        .alert("Delete Account", isPresented: $showDeleteStep1) {
            Button("Continue", role: .destructive) {
                deleteConfirmationText = ""
                showDeleteStep2 = true
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will permanently delete your account, all invoices, company data, and subscription. This action cannot be undone.")
        }
        // Step 2 — type DELETE to confirm
        .alert("Type DELETE to Confirm", isPresented: $showDeleteStep2) {
            TextField("Type DELETE", text: $deleteConfirmationText)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.characters)
            Button("Delete My Account", role: .destructive) {
                guard deleteConfirmed else { return }
                Task { await performDelete() }
            }
            .disabled(!deleteConfirmed)
            Button("Cancel", role: .cancel) {
                deleteConfirmationText = ""
            }
        } message: {
            Text("Type DELETE in all caps to permanently delete your account.")
        }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: {
            if let msg = errorMessage { Text(msg) }
        }
    }

    // MARK: - Sections

    private var accountInfoSection: some View {
        Section("Account Information") {
            LabeledContent("Email", value: currentEmail)

            if let tier = appState.auth.currentUser?.subscriptionTier {
                LabeledContent("Plan", value: tier.capitalized)
            }
        }
    }

    private var dangerZoneSection: some View {
        Section {
            Button(role: .destructive) {
                showDeleteStep1 = true
            } label: {
                HStack {
                    Spacer()
                    if isDeleting {
                        ProgressView()
                            .scaleEffect(0.8)
                        Text("Deleting Account...")
                            .foregroundStyle(.red)
                    } else {
                        Label("Delete Account", systemImage: "trash.fill")
                            .foregroundStyle(.red)
                    }
                    Spacer()
                }
            }
            .disabled(isDeleting)
        } header: {
            Text("Danger Zone")
        } footer: {
            Text("Deleting your account permanently removes all data including invoices, clients, and company information. Active subscriptions will be cancelled. This cannot be undone.")
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Actions

    @MainActor
    private func performDelete() async {
        isDeleting = true
        defer { isDeleting = false }
        do {
            try await appState.auth.deleteAccount()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        AccountView()
            .environment(AppState())
    }
}
