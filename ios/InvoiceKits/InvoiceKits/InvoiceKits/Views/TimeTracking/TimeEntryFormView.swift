import SwiftUI

struct TimeEntryFormView: View {
    let entry: TimeEntryResponse?
    var onSave: (() -> Void)?

    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    // MARK: - Form State

    @State private var descriptionText = ""
    @State private var clientName = ""
    @State private var clientEmail = ""
    @State private var hours = 0
    @State private var minutes = 0
    @State private var hourlyRate = ""
    @State private var date = Date()

    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var showError = false

    private var isEditing: Bool { entry != nil }
    private var title: String { isEditing ? "Edit Entry" : "New Entry" }

    // MARK: - Body

    var body: some View {
        Form {
            // MARK: Work Details
            Section("Work Details") {
                TextField("Description", text: $descriptionText, axis: .vertical)
                    .lineLimit(3...)
                    .accessibilityLabel("Entry description")
            }

            // MARK: Client
            Section("Client (Optional)") {
                TextField("Client name", text: $clientName)
                    .textContentType(.name)

                TextField("Client email", text: $clientEmail)
                    .textContentType(.emailAddress)
                    .keyboardType(.emailAddress)
                    .autocapitalization(.none)
                    .autocorrectionDisabled()
            }

            // MARK: Duration
            Section("Duration") {
                HStack {
                    Text("Hours")
                        .foregroundStyle(.secondary)
                    Spacer()
                    Picker("Hours", selection: $hours) {
                        ForEach(0...23, id: \.self) { h in
                            Text("\(h)").tag(h)
                        }
                    }
                    .pickerStyle(.wheel)
                    .frame(width: 80, height: 100)
                    .clipped()
                    .accessibilityLabel("Hours")
                }

                HStack {
                    Text("Minutes")
                        .foregroundStyle(.secondary)
                    Spacer()
                    Picker("Minutes", selection: $minutes) {
                        ForEach(0...59, id: \.self) { m in
                            Text("\(m)").tag(m)
                        }
                    }
                    .pickerStyle(.wheel)
                    .frame(width: 80, height: 100)
                    .clipped()
                    .accessibilityLabel("Minutes")
                }
            }

            // MARK: Rate & Date
            Section("Rate & Date") {
                HStack {
                    Text("$")
                        .foregroundStyle(.secondary)
                    TextField("Hourly rate", text: $hourlyRate)
                        .keyboardType(.decimalPad)
                        .accessibilityLabel("Hourly rate")
                }

                DatePicker("Date", selection: $date, displayedComponents: .date)
                    .accessibilityLabel("Entry date")
            }
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Cancel") { dismiss() }
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Save") {
                    Task { await save() }
                }
                .fontWeight(.semibold)
                .disabled(isSaving || !isFormValid)
            }
        }
        .overlay {
            if isSaving {
                ZStack {
                    Color(.systemBackground).opacity(0.6)
                    ProgressView()
                }
                .ignoresSafeArea()
            }
        }
        .alert("Save Failed", isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "An unexpected error occurred.")
        }
        .onAppear {
            populateFromEntry()
        }
    }

    // MARK: - Validation

    private var isFormValid: Bool {
        !descriptionText.trimmingCharacters(in: .whitespaces).isEmpty
            && (hours > 0 || minutes > 0)
    }

    // MARK: - Populate from existing entry

    private func populateFromEntry() {
        guard let e = entry else { return }
        descriptionText = e.description
        clientName = e.clientName ?? ""
        clientEmail = e.clientEmail ?? ""

        let totalSeconds = e.durationSeconds
        hours = totalSeconds / 3600
        minutes = (totalSeconds % 3600) / 60

        hourlyRate = e.hourlyRate

        // Parse ISO date string "YYYY-MM-DD"
        let df = DateFormatter()
        df.dateFormat = "yyyy-MM-dd"
        date = df.date(from: e.date) ?? Date()
    }

    // MARK: - Save

    private func save() async {
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        let df = DateFormatter()
        df.dateFormat = "yyyy-MM-dd"
        let dateString = df.string(from: date)

        struct EntryBody: Encodable {
            let description: String
            let clientName: String
            let clientEmail: String
            let hours: Int
            let minutes: Int
            let hourlyRate: String
            let date: String
        }

        let body = EntryBody(
            description: descriptionText.trimmingCharacters(in: .whitespaces),
            clientName: clientName,
            clientEmail: clientEmail,
            hours: hours,
            minutes: minutes,
            hourlyRate: hourlyRate.isEmpty ? "0" : hourlyRate,
            date: dateString
        )

        do {
            if let existing = entry {
                let _: TimeEntryResponse = try await appState.api.put(
                    "time/entries/\(existing.id)/",
                    body: body
                )
            } else {
                let _: TimeEntryResponse = try await appState.api.post(
                    "time/entries/",
                    body: body
                )
            }
            await MainActor.run {
                onSave?()
                dismiss()
            }
        } catch {
            await MainActor.run {
                errorMessage = error.localizedDescription
                showError = true
            }
        }
    }
}

#Preview("New Entry") {
    NavigationStack {
        TimeEntryFormView(entry: nil)
            .environment(AppState())
    }
}
