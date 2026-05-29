import SwiftUI

// MARK: - Response Model

struct ReminderSettingsResponse: Codable {
    let remindersEnabled: Bool
    let remind3DaysBefore: Bool
    let remind1DayBefore: Bool
    let remindOnDueDate: Bool
    let remind3DaysAfter: Bool
    let remind7DaysAfter: Bool
    let remind14DaysAfter: Bool
    let ccBusinessOwner: Bool
    let customMessageBefore: String?
    let customMessageDue: String?
    let customMessageOverdue: String?
}

// MARK: - View

struct ReminderSettingsView: View {
    @Environment(AppState.self) private var appState

    // MARK: - Form State

    @State private var remindersEnabled = true
    @State private var daysBefore3 = true
    @State private var daysBefore1 = true
    @State private var onDueDate = true
    @State private var daysAfter3 = true
    @State private var daysAfter7 = true
    @State private var daysAfter14 = false
    @State private var ccBusinessOwner = false
    @State private var messageBeforeDue = ""
    @State private var messageOnDueDate = ""
    @State private var messageOverdue = ""

    @State private var isLoading = false
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var showSuccessBanner = false

    var body: some View {
        Form {
            masterToggleSection
            if remindersEnabled {
                scheduleSection
                notificationsSection
                messagesSection
            }
        }
        .navigationTitle("Payment Reminders")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Save") {
                    Task { await save() }
                }
                .disabled(isSaving)
                .overlay {
                    if isSaving { ProgressView().scaleEffect(0.7) }
                }
            }
        }
        .task { await load() }
        .overlay(alignment: .top) {
            if showSuccessBanner { successBanner }
        }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: {
            if let msg = errorMessage { Text(msg) }
        }
    }

    // MARK: - Sections

    private var masterToggleSection: some View {
        Section {
            Toggle("Enable Payment Reminders", isOn: $remindersEnabled)
        } footer: {
            Text("When enabled, InvoiceKits will automatically email clients based on the schedule below.")
        }
    }

    private var scheduleSection: some View {
        Section("Reminder Schedule") {
            VStack(alignment: .leading, spacing: 16) {
                Text("Before Due Date")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundStyle(.secondary)
                Toggle("3 days before", isOn: $daysBefore3)
                Toggle("1 day before", isOn: $daysBefore1)
            }

            VStack(alignment: .leading, spacing: 16) {
                Text("On Due Date")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundStyle(.secondary)
                Toggle("On the due date", isOn: $onDueDate)
            }

            VStack(alignment: .leading, spacing: 16) {
                Text("After Due Date")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundStyle(.secondary)
                Toggle("3 days after", isOn: $daysAfter3)
                Toggle("7 days after", isOn: $daysAfter7)
                Toggle("14 days after", isOn: $daysAfter14)
            }
        }
    }

    private var notificationsSection: some View {
        Section {
            Toggle("CC me on all reminders", isOn: $ccBusinessOwner)
        } header: {
            Text("Notifications")
        } footer: {
            Text("Sends a copy of each reminder to your account email address.")
        }
    }

    private var messagesSection: some View {
        Section {
            messageField(
                label: "Before Due Date (Friendly)",
                placeholder: "e.g. Just a friendly reminder that invoice #INV-001 is due on {due_date}.",
                text: $messageBeforeDue
            )

            messageField(
                label: "On Due Date (Firm)",
                placeholder: "e.g. Your invoice #INV-001 is due today. Please arrange payment at your earliest convenience.",
                text: $messageOnDueDate
            )

            messageField(
                label: "Overdue (Urgent)",
                placeholder: "e.g. Invoice #INV-001 is now overdue. Please contact us immediately.",
                text: $messageOverdue
            )
        } header: {
            Text("Custom Messages")
        } footer: {
            Text("Leave blank to use the default InvoiceKits message for each stage.")
        }
    }

    private func messageField(label: String, placeholder: String, text: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundStyle(.secondary)
            TextEditor(text: text)
                .frame(minHeight: 80)
                .overlay(alignment: .topLeading) {
                    if text.wrappedValue.isEmpty {
                        Text(placeholder)
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                            .padding(.top, 8)
                            .padding(.leading, 4)
                            .allowsHitTesting(false)
                    }
                }
        }
        .padding(.vertical, 4)
    }

    private var successBanner: some View {
        Text("Reminder settings saved.")
            .font(.subheadline)
            .fontWeight(.medium)
            .foregroundStyle(.white)
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(Color.green, in: Capsule())
            .padding(.top, 8)
            .transition(.move(edge: .top).combined(with: .opacity))
            .onAppear {
                DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
                    withAnimation { showSuccessBanner = false }
                }
            }
    }

    // MARK: - Data

    @MainActor
    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let settings: ReminderSettingsResponse = try await appState.api.get("settings/reminders/")
            remindersEnabled  = settings.remindersEnabled
            daysBefore3       = settings.remind3DaysBefore
            daysBefore1       = settings.remind1DayBefore
            onDueDate         = settings.remindOnDueDate
            daysAfter3        = settings.remind3DaysAfter
            daysAfter7        = settings.remind7DaysAfter
            daysAfter14       = settings.remind14DaysAfter
            ccBusinessOwner   = settings.ccBusinessOwner
            messageBeforeDue  = settings.customMessageBefore ?? ""
            messageOnDueDate  = settings.customMessageDue ?? ""
            messageOverdue    = settings.customMessageOverdue ?? ""
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    struct ReminderSettingsRequest: Encodable {
        let remindersEnabled: Bool
        let remind3DaysBefore: Bool
        let remind1DayBefore: Bool
        let remindOnDueDate: Bool
        let remind3DaysAfter: Bool
        let remind7DaysAfter: Bool
        let remind14DaysAfter: Bool
        let ccBusinessOwner: Bool
        let customMessageBefore: String?
        let customMessageDue: String?
        let customMessageOverdue: String?
    }

    @MainActor
    private func save() async {
        isSaving = true
        defer { isSaving = false }
        do {
            let body = ReminderSettingsRequest(
                remindersEnabled:     remindersEnabled,
                remind3DaysBefore:    daysBefore3,
                remind1DayBefore:     daysBefore1,
                remindOnDueDate:      onDueDate,
                remind3DaysAfter:     daysAfter3,
                remind7DaysAfter:     daysAfter7,
                remind14DaysAfter:    daysAfter14,
                ccBusinessOwner:      ccBusinessOwner,
                customMessageBefore:  messageBeforeDue.isEmpty ? nil : messageBeforeDue,
                customMessageDue:     messageOnDueDate.isEmpty ? nil : messageOnDueDate,
                customMessageOverdue: messageOverdue.isEmpty ? nil : messageOverdue
            )
            let _: ReminderSettingsResponse = try await appState.api.put("settings/reminders/", body: body)
            withAnimation { showSuccessBanner = true }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        ReminderSettingsView()
            .environment(AppState())
    }
}
