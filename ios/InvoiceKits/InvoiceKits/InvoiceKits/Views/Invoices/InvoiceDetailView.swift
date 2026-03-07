import SwiftUI

struct InvoiceDetailView: View {
    @Environment(AppState.self) private var appState

    let invoiceId: Int

    @State private var invoice: InvoiceResponse?
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showDeleteConfirm = false
    @State private var isSending = false
    @State private var isMarkingPaid = false
    @State private var showPDFPreview = false
    @State private var showRecurringForm = false
    @State private var actionError: String?
    @State private var showActionError = false

    // MARK: - Body

    var body: some View {
        Group {
            if isLoading && invoice == nil {
                ProgressView("Loading invoice...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let invoice {
                invoiceContent(invoice)
            } else if let errorMessage {
                ContentUnavailableView(
                    "Failed to Load",
                    systemImage: "exclamationmark.triangle",
                    description: Text(errorMessage)
                )
            }
        }
        .navigationTitle(invoice?.invoiceNumber ?? "Invoice")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if let invoice {
                toolbarItems(for: invoice)
            }
        }
        .alert("Delete Invoice", isPresented: $showDeleteConfirm) {
            Button("Delete", role: .destructive) {
                Task { await deleteInvoice() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            if let invoice {
                Text("Delete invoice \(invoice.invoiceNumber) for \(invoice.clientName)? This cannot be undone.")
            }
        }
        .alert("Action Failed", isPresented: $showActionError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(actionError ?? "An unexpected error occurred.")
        }
        .sheet(isPresented: $showPDFPreview) {
            // Placeholder until PDFPreviewView is implemented
            NavigationStack {
                Text("PDF Preview")
                    .navigationTitle("PDF Preview")
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("Done") { showPDFPreview = false }
                        }
                    }
            }
        }
        .sheet(isPresented: $showRecurringForm) {
            // Placeholder until RecurringInvoiceFormView is implemented
            NavigationStack {
                Text("Make Recurring")
                    .navigationTitle("Make Recurring")
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("Cancel") { showRecurringForm = false }
                        }
                    }
            }
        }
        .task {
            await loadInvoice()
        }
    }

    // MARK: - Main Content

    @ViewBuilder
    private func invoiceContent(_ invoice: InvoiceResponse) -> some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                headerSection(invoice)
                Divider().padding(.horizontal)

                clientSection(invoice)
                Divider().padding(.horizontal)

                if let lineItems = invoice.lineItems, !lineItems.isEmpty {
                    lineItemsSection(lineItems, currencySymbol: invoice.currencySymbol)
                    Divider().padding(.horizontal)
                }

                financialSummarySection(invoice)

                if let notes = invoice.notes, !notes.isEmpty {
                    Divider().padding(.horizontal)
                    notesSection(notes)
                }

                togglesSection(invoice)

                deleteSection
            }
        }
    }

    // MARK: - Header Section

    private func headerSection(_ invoice: InvoiceResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(invoice.invoiceNumber)
                        .font(.title2)
                        .fontWeight(.bold)
                    if let name = invoice.invoiceName, !name.isEmpty {
                        Text(name)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                StatusBadge(status: invoice.status)
            }

            HStack(spacing: 24) {
                LabeledValue(
                    label: "Invoice Date",
                    value: formattedDate(invoice.invoiceDate)
                )
                LabeledValue(
                    label: "Due Date",
                    value: formattedDate(invoice.dueDate)
                )
                LabeledValue(
                    label: "Terms",
                    value: invoice.paymentTerms
                )
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
    }

    // MARK: - Client Section

    private func clientSection(_ invoice: InvoiceResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Bill To")

            VStack(alignment: .leading, spacing: 6) {
                Text(invoice.clientName)
                    .font(.headline)

                if !invoice.clientEmail.isEmpty {
                    Label(invoice.clientEmail, systemImage: "envelope")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if let phone = invoice.clientPhone, !phone.isEmpty {
                    Label(phone, systemImage: "phone")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if let address = invoice.clientAddress, !address.isEmpty {
                    Label(address, systemImage: "mappin")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
    }

    // MARK: - Line Items Section

    private func lineItemsSection(_ lineItems: [LineItemResponse], currencySymbol: String) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Line Items")

            VStack(spacing: 0) {
                // Table header
                HStack {
                    Text("Description")
                        .frame(maxWidth: .infinity, alignment: .leading)
                    Text("Qty")
                        .frame(width: 44, alignment: .trailing)
                    Text("Rate")
                        .frame(width: 72, alignment: .trailing)
                    Text("Total")
                        .frame(width: 80, alignment: .trailing)
                }
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundStyle(.secondary)
                .padding(.horizontal)
                .padding(.bottom, 6)

                Divider().padding(.horizontal)

                ForEach(lineItems) { item in
                    HStack(alignment: .top) {
                        Text(item.description)
                            .font(.subheadline)
                            .frame(maxWidth: .infinity, alignment: .leading)
                        Text(item.quantity)
                            .font(.subheadline)
                            .frame(width: 44, alignment: .trailing)
                            .monospacedDigit()
                        Text("\(currencySymbol)\(item.unitPrice)")
                            .font(.subheadline)
                            .frame(width: 72, alignment: .trailing)
                            .monospacedDigit()
                        Text("\(currencySymbol)\(item.total)")
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .frame(width: 80, alignment: .trailing)
                            .monospacedDigit()
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 8)

                    if item.id != lineItems.last?.id {
                        Divider()
                            .padding(.horizontal)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical)
    }

    // MARK: - Financial Summary Section

    private func financialSummarySection(_ invoice: InvoiceResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Summary")

            VStack(spacing: 8) {
                FinancialRow(
                    label: "Subtotal",
                    value: "\(invoice.currencySymbol)\(invoice.subtotal)"
                )

                let taxRate = Double(invoice.taxRate) ?? 0
                if taxRate > 0 {
                    FinancialRow(
                        label: "Tax (\(invoice.taxRate)%)",
                        value: "\(invoice.currencySymbol)\(invoice.taxAmount)"
                    )
                }

                let discount = Double(invoice.discountAmount) ?? 0
                if discount > 0 {
                    FinancialRow(
                        label: "Discount",
                        value: "-\(invoice.currencySymbol)\(invoice.discountAmount)",
                        valueColor: .green
                    )
                }

                Divider()

                HStack {
                    Text("Total")
                        .font(.headline)
                        .fontWeight(.bold)
                    Spacer()
                    Text("\(invoice.currencySymbol)\(invoice.total)")
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundStyle(Color.accentColor)
                }
                .padding(.horizontal)
                .padding(.vertical, 8)
                .background(Color.accentColor.opacity(0.08), in: RoundedRectangle(cornerRadius: 10))
                .padding(.horizontal)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical)
    }

    // MARK: - Notes Section

    private func notesSection(_ notes: String) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Notes")
            Text(notes)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal)
        }
        .padding(.vertical)
    }

    // MARK: - Toggles Section

    private func togglesSection(_ invoice: InvoiceResponse) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Divider().padding(.horizontal)

            SectionHeader(title: "Settings")
                .padding(.horizontal)
                .padding(.top, 16)

            VStack(spacing: 0) {
                ReminderToggleRow(
                    isPaused: invoice.remindersPaused,
                    invoiceId: invoice.id,
                    appState: appState,
                    onUpdate: { updated in
                        self.invoice = updated
                    }
                )

                Divider().padding(.horizontal)

                LateFeeToggleRow(
                    isPaused: invoice.lateFeesPaused,
                    lateFeeApplied: invoice.lateFeeApplied,
                    invoiceId: invoice.id,
                    appState: appState,
                    onUpdate: { updated in
                        self.invoice = updated
                    }
                )
            }
            .padding(.bottom, 8)
        }
    }

    // MARK: - Delete Section

    private var deleteSection: some View {
        VStack {
            Divider().padding(.horizontal)
            Button(role: .destructive) {
                showDeleteConfirm = true
            } label: {
                Label("Delete Invoice", systemImage: "trash")
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
            }
            .buttonStyle(.bordered)
            .tint(.red)
            .padding()
        }
    }

    // MARK: - Toolbar

    @ToolbarContentBuilder
    private func toolbarItems(for invoice: InvoiceResponse) -> some ToolbarContent {
        ToolbarItemGroup(placement: .primaryAction) {
            // Make Recurring
            Button {
                showRecurringForm = true
            } label: {
                Image(systemName: "arrow.clockwise")
            }
            .help("Make Recurring")

            // PDF
            Button {
                showPDFPreview = true
            } label: {
                Image(systemName: "doc.richtext")
            }
            .help("View PDF")

            // Mark Paid (only when not already paid)
            if invoice.status.lowercased() != "paid" {
                Button {
                    Task { await markPaid() }
                } label: {
                    if isMarkingPaid {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Image(systemName: "checkmark.circle")
                    }
                }
                .disabled(isMarkingPaid)
                .help("Mark as Paid")
            }

            // Send
            Button {
                Task { await sendInvoice() }
            } label: {
                if isSending {
                    ProgressView()
                        .controlSize(.small)
                } else {
                    Image(systemName: "envelope")
                }
            }
            .disabled(isSending)
            .help("Send Invoice")
        }
    }

    // MARK: - Actions

    @MainActor
    private func loadInvoice() async {
        isLoading = true
        defer { isLoading = false }
        do {
            invoice = try await appState.api.get("invoices/\(invoiceId)/")
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func sendInvoice() async {
        isSending = true
        defer { isSending = false }
        do {
            let updated: InvoiceResponse = try await appState.api.post("invoices/\(invoiceId)/send/")
            HapticManager.notification(.success)
            invoice = updated
        } catch {
            actionError = "Failed to send invoice. Please try again."
            showActionError = true
        }
    }

    @MainActor
    private func markPaid() async {
        isMarkingPaid = true
        defer { isMarkingPaid = false }
        do {
            let updated: InvoiceResponse = try await appState.api.post("invoices/\(invoiceId)/mark-paid/")
            HapticManager.notification(.success)
            invoice = updated
        } catch {
            actionError = "Failed to mark as paid. Please try again."
            showActionError = true
        }
    }

    @MainActor
    private func deleteInvoice() async {
        do {
            try await appState.api.delete("invoices/\(invoiceId)/")
            HapticManager.notification(.warning)
        } catch {
            actionError = "Failed to delete invoice. Please try again."
            showActionError = true
        }
    }

    // MARK: - Helpers

    private func formattedDate(_ dateString: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        guard let date = formatter.date(from: dateString) else { return dateString }
        return date.formatted(date: .abbreviated, time: .omitted)
    }
}

// MARK: - Supporting Views

private struct SectionHeader: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.footnote)
            .fontWeight(.semibold)
            .foregroundStyle(.secondary)
            .textCase(.uppercase)
            .padding(.horizontal)
    }
}

private struct LabeledValue: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.caption2)
                .foregroundStyle(.tertiary)
                .textCase(.uppercase)
            Text(value)
                .font(.caption)
                .fontWeight(.medium)
        }
    }
}

private struct FinancialRow: View {
    let label: String
    let value: String
    var valueColor: Color = .primary

    var body: some View {
        HStack {
            Text(label)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundStyle(valueColor)
                .monospacedDigit()
        }
        .padding(.horizontal)
    }
}

// MARK: - Reminder Toggle Row

private struct ReminderToggleRow: View {
    let isPaused: Bool
    let invoiceId: Int
    let appState: AppState
    let onUpdate: (InvoiceResponse) -> Void

    @State private var isToggling = false
    @State private var localPaused: Bool

    init(isPaused: Bool, invoiceId: Int, appState: AppState, onUpdate: @escaping (InvoiceResponse) -> Void) {
        self.isPaused = isPaused
        self.invoiceId = invoiceId
        self.appState = appState
        self.onUpdate = onUpdate
        self._localPaused = State(initialValue: isPaused)
    }

    var body: some View {
        HStack {
            Label(
                "Payment Reminders",
                systemImage: "bell"
            )
            Spacer()
            if isToggling {
                ProgressView()
                    .controlSize(.small)
            } else {
                Toggle("", isOn: Binding(
                    get: { !localPaused },
                    set: { _ in Task { await toggle() } }
                ))
                .labelsHidden()
            }
        }
        .padding()
    }

    @MainActor
    private func toggle() async {
        isToggling = true
        defer { isToggling = false }
        do {
            let updated: InvoiceResponse = try await appState.api.post(
                "invoices/\(invoiceId)/toggle-reminders/"
            )
            localPaused = updated.remindersPaused
            onUpdate(updated)
        } catch {
            // Silently revert on failure — the toggle binding handles optimistic state
        }
    }
}

// MARK: - Late Fee Toggle Row

private struct LateFeeToggleRow: View {
    let isPaused: Bool
    let lateFeeApplied: String?
    let invoiceId: Int
    let appState: AppState
    let onUpdate: (InvoiceResponse) -> Void

    @State private var isToggling = false
    @State private var localPaused: Bool

    init(isPaused: Bool, lateFeeApplied: String?, invoiceId: Int, appState: AppState, onUpdate: @escaping (InvoiceResponse) -> Void) {
        self.isPaused = isPaused
        self.lateFeeApplied = lateFeeApplied
        self.invoiceId = invoiceId
        self.appState = appState
        self.onUpdate = onUpdate
        self._localPaused = State(initialValue: isPaused)
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Label("Late Fees", systemImage: "exclamationmark.circle")
                if let applied = lateFeeApplied {
                    Text("Applied: \(applied)")
                        .font(.caption)
                        .foregroundStyle(.orange)
                }
            }
            Spacer()
            if isToggling {
                ProgressView()
                    .controlSize(.small)
            } else {
                Toggle("", isOn: Binding(
                    get: { !localPaused },
                    set: { _ in Task { await toggle() } }
                ))
                .labelsHidden()
            }
        }
        .padding()
    }

    @MainActor
    private func toggle() async {
        isToggling = true
        defer { isToggling = false }
        do {
            let updated: InvoiceResponse = try await appState.api.post(
                "invoices/\(invoiceId)/toggle-late-fees/"
            )
            localPaused = updated.lateFeesPaused
            onUpdate(updated)
        } catch {
            // Silently revert on failure
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        InvoiceDetailView(invoiceId: 1)
            .environment(AppState())
    }
}
