import SwiftUI

struct RecurringDetailView: View {
    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    let recurringId: Int

    @State private var item: RecurringInvoiceResponse?
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showEditForm = false
    @State private var showDeleteConfirm = false
    @State private var isGenerating = false
    @State private var isTogglingStatus = false

    var body: some View {
        Group {
            if isLoading && item == nil {
                ProgressView("Loading...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let item {
                detailContent(item)
            } else if let errorMessage {
                ContentUnavailableView {
                    Label("Failed to Load", systemImage: "exclamationmark.triangle")
                } description: {
                    Text(errorMessage)
                } actions: {
                    Button("Retry") { Task { await load() } }
                        .buttonStyle(.borderedProminent)
                }
            }
        }
        .navigationTitle("Recurring Invoice")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .sheet(isPresented: $showEditForm) {
            if let item {
                RecurringFormView(existing: item) {
                    Task { await load() }
                }
            }
        }
        .alert("Delete Recurring Invoice", isPresented: $showDeleteConfirm) {
            Button("Delete", role: .destructive) {
                Task { await delete() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            if let item {
                Text("Delete the recurring invoice for \(item.clientName)? All previously generated invoices will be kept.")
            }
        }
    }

    // MARK: - Detail Content

    @ViewBuilder
    private func detailContent(_ item: RecurringInvoiceResponse) -> some View {
        List {
            // MARK: Schedule Section
            Section("Schedule") {
                LabeledContent("Frequency", value: frequencyLabel(item.frequency))
                LabeledContent("Status") {
                    Text(item.status.uppercased())
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(item.status.lowercased() == "active" ? Color.green : Color.orange, in: Capsule())
                }
                LabeledContent("Start Date", value: formattedDate(item.startDate))
                if let end = item.endDate {
                    LabeledContent("End Date", value: formattedDate(end))
                }
                if let next = item.nextGenerationDate {
                    LabeledContent("Next Generation", value: formattedDate(next))
                }
            }

            // MARK: Client Section
            Section("Client") {
                LabeledContent("Name", value: item.clientName)
                LabeledContent("Email", value: item.clientEmail)
                if let phone = item.clientPhone, !phone.isEmpty {
                    LabeledContent("Phone", value: phone)
                }
                if let address = item.clientAddress, !address.isEmpty {
                    LabeledContent("Address", value: address)
                }
            }

            // MARK: Invoice Details Section
            Section("Invoice Details") {
                if let name = item.invoiceName, !name.isEmpty {
                    LabeledContent("Invoice Name", value: name)
                }
                LabeledContent("Currency", value: item.currency)
                if let terms = item.defaultPaymentTerms, !terms.isEmpty {
                    LabeledContent("Payment Terms", value: terms)
                }
                if let taxRate = item.taxRate {
                    LabeledContent("Tax Rate", value: "\(taxRate)%")
                }
                if let discount = item.discountAmount {
                    LabeledContent("Discount", value: "\(item.currencySymbol)\(discount)")
                }
                LabeledContent("Total", value: "\(item.currencySymbol)\(item.total)")
                    .fontWeight(.semibold)
            }

            // MARK: Line Items Section
            if let lineItems = item.lineItems, !lineItems.isEmpty {
                Section("Line Items") {
                    ForEach(lineItems) { lineItem in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(lineItem.description)
                                .font(.body)
                            HStack {
                                Text("\(lineItem.quantity) x \(item.currencySymbol)\(lineItem.unitPrice)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text("\(item.currencySymbol)\(lineItem.total)")
                                    .font(.caption)
                                    .fontWeight(.medium)
                            }
                        }
                        .padding(.vertical, 2)
                    }
                }
            }

            // MARK: Notes Section
            if let notes = item.notes, !notes.isEmpty {
                Section("Notes") {
                    Text(notes)
                        .font(.body)
                        .foregroundStyle(.secondary)
                }
            }

            // MARK: Actions Section
            Section {
                // Toggle pause / resume
                Button {
                    Task { await toggleStatus() }
                } label: {
                    HStack {
                        if isTogglingStatus {
                            ProgressView()
                                .scaleEffect(0.8)
                        }
                        Label(
                            item.status.lowercased() == "active" ? "Pause Recurring" : "Resume Recurring",
                            systemImage: item.status.lowercased() == "active" ? "pause.circle" : "play.circle"
                        )
                        .foregroundStyle(item.status.lowercased() == "active" ? .orange : .green)
                    }
                }
                .disabled(isTogglingStatus)

                // Generate now
                Button {
                    Task { await generateNow() }
                } label: {
                    HStack {
                        if isGenerating {
                            ProgressView()
                                .scaleEffect(0.8)
                        }
                        Label("Generate Invoice Now", systemImage: "bolt.circle")
                            .foregroundStyle(.blue)
                    }
                }
                .disabled(isGenerating || item.status.lowercased() == "paused")

                // Edit
                Button {
                    showEditForm = true
                } label: {
                    Label("Edit", systemImage: "pencil")
                }

                // Delete
                Button(role: .destructive) {
                    showDeleteConfirm = true
                } label: {
                    Label("Delete", systemImage: "trash")
                }
            }
        }
        .listStyle(.insetGrouped)
    }

    // MARK: - Helpers

    private func frequencyLabel(_ frequency: String) -> String {
        switch frequency.lowercased() {
        case "weekly":     return "Weekly"
        case "bi_weekly":  return "Every 2 Weeks"
        case "monthly":    return "Monthly"
        case "quarterly":  return "Quarterly"
        case "yearly":     return "Yearly"
        default:           return frequency.capitalized
        }
    }

    private func formattedDate(_ raw: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        guard let date = formatter.date(from: raw) else { return raw }
        return date.formatted(date: .abbreviated, time: .omitted)
    }

    // MARK: - Actions

    @MainActor
    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            item = try await appState.api.get("recurring/\(recurringId)/")
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func toggleStatus() async {
        isTogglingStatus = true
        defer { isTogglingStatus = false }
        do {
            let updated: RecurringInvoiceResponse = try await appState.api.post("recurring/\(recurringId)/toggle-status/")
            item = updated
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func generateNow() async {
        isGenerating = true
        defer { isGenerating = false }
        do {
            let _: InvoiceResponse = try await appState.api.post("recurring/\(recurringId)/generate-now/")
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func delete() async {
        do {
            try await appState.api.delete("recurring/\(recurringId)/")
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        RecurringDetailView(recurringId: 1)
            .environment(AppState())
    }
}
