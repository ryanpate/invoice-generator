import SwiftUI

struct RecurringFormView: View {
    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    let existing: RecurringInvoiceResponse?
    let onSave: () -> Void

    // MARK: - Client Fields

    @State private var clientName = ""
    @State private var clientEmail = ""
    @State private var clientPhone = ""
    @State private var clientAddress = ""

    // MARK: - Invoice Fields

    @State private var invoiceName = ""
    @State private var currency = "USD"
    @State private var taxRate = ""
    @State private var discountAmount = ""
    @State private var notes = ""
    @State private var paymentTerms = "net_30"
    @State private var templateStyle = "clean_slate"

    // MARK: - Schedule Fields

    @State private var frequency: Frequency = .monthly
    @State private var startDate = Date()
    @State private var hasEndDate = false
    @State private var endDate = Calendar.current.date(byAdding: .year, value: 1, to: Date()) ?? Date()

    // MARK: - Line Items

    @State private var lineItems: [DraftLineItem] = [DraftLineItem()]

    // MARK: - UI State

    @State private var isSaving = false
    @State private var errorMessage: String?

    // MARK: - Types

    enum Frequency: String, CaseIterable, Identifiable {
        case weekly     = "weekly"
        case biWeekly   = "bi_weekly"
        case monthly    = "monthly"
        case quarterly  = "quarterly"
        case yearly     = "yearly"

        var id: String { rawValue }

        var label: String {
            switch self {
            case .weekly:    return "Weekly"
            case .biWeekly:  return "Every 2 Weeks"
            case .monthly:   return "Monthly"
            case .quarterly: return "Quarterly"
            case .yearly:    return "Yearly"
            }
        }
    }

    struct DraftLineItem: Identifiable {
        let id = UUID()
        var description = ""
        var quantity = "1"
        var unitPrice = ""

        var computedTotal: Double {
            let q = Double(quantity) ?? 0
            let p = Double(unitPrice) ?? 0
            return q * p
        }
    }

    // MARK: - Computed

    private var isEditing: Bool { existing != nil }

    private var title: String { isEditing ? "Edit Recurring" : "New Recurring Invoice" }

    private var computedSubtotal: Double {
        lineItems.reduce(0) { $0 + $1.computedTotal }
    }

    private var computedTax: Double {
        let rate = Double(taxRate) ?? 0
        return computedSubtotal * (rate / 100)
    }

    private var computedDiscount: Double { Double(discountAmount) ?? 0 }

    private var computedTotal: Double { computedSubtotal + computedTax - computedDiscount }

    // MARK: - Init

    init(existing: RecurringInvoiceResponse?, onSave: @escaping () -> Void) {
        self.existing = existing
        self.onSave = onSave

        if let e = existing {
            _clientName    = State(initialValue: e.clientName)
            _clientEmail   = State(initialValue: e.clientEmail)
            _clientPhone   = State(initialValue: e.clientPhone ?? "")
            _clientAddress = State(initialValue: e.clientAddress ?? "")
            _invoiceName   = State(initialValue: e.invoiceName ?? "")
            _currency      = State(initialValue: e.currency)
            _taxRate       = State(initialValue: e.taxRate ?? "")
            _discountAmount = State(initialValue: e.discountAmount ?? "")
            _notes         = State(initialValue: e.notes ?? "")
            _paymentTerms  = State(initialValue: e.defaultPaymentTerms ?? "net_30")
            _templateStyle = State(initialValue: e.templateStyle ?? "clean_slate")
            _frequency     = State(initialValue: Frequency(rawValue: e.frequency) ?? .monthly)

            let isoFull = ISO8601DateFormatter()
            if let d = isoFull.date(from: e.startDate) {
                _startDate = State(initialValue: d)
            }
            if let end = e.endDate, let d = isoFull.date(from: end) {
                _hasEndDate = State(initialValue: true)
                _endDate = State(initialValue: d)
            }
            let drafts = (e.lineItems ?? []).map { li in
                var d = DraftLineItem()
                d.description = li.description
                d.quantity    = li.quantity
                d.unitPrice   = li.unitPrice
                return d
            }
            _lineItems = State(initialValue: drafts.isEmpty ? [DraftLineItem()] : drafts)
        }
    }

    // MARK: - Body

    var body: some View {
        NavigationStack {
            Form {
                clientSection
                scheduleSection
                lineItemsSection
                invoiceDetailsSection
                notesSection
                summarySection
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await save() }
                    }
                    .disabled(isSaving || clientName.isEmpty || clientEmail.isEmpty || lineItems.allSatisfy { $0.description.isEmpty })
                    .overlay {
                        if isSaving { ProgressView().scaleEffect(0.7) }
                    }
                }
            }
            .alert("Error", isPresented: .constant(errorMessage != nil)) {
                Button("OK") { errorMessage = nil }
            } message: {
                if let msg = errorMessage { Text(msg) }
            }
        }
    }

    // MARK: - Sections

    private var clientSection: some View {
        Section("Client") {
            TextField("Client Name *", text: $clientName)
                .textContentType(.organizationName)
                .autocorrectionDisabled()
            TextField("Client Email *", text: $clientEmail)
                .textContentType(.emailAddress)
                .keyboardType(.emailAddress)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
            TextField("Phone", text: $clientPhone)
                .textContentType(.telephoneNumber)
                .keyboardType(.phonePad)
            TextField("Address", text: $clientAddress)
                .textContentType(.fullStreetAddress)
        }
    }

    private var scheduleSection: some View {
        Section("Schedule") {
            Picker("Frequency", selection: $frequency) {
                ForEach(Frequency.allCases) { freq in
                    Text(freq.label).tag(freq)
                }
            }

            DatePicker("Start Date", selection: $startDate, displayedComponents: .date)

            Toggle("Has End Date", isOn: $hasEndDate)

            if hasEndDate {
                DatePicker(
                    "End Date",
                    selection: $endDate,
                    in: startDate...,
                    displayedComponents: .date
                )
            }
        }
    }

    private var lineItemsSection: some View {
        Section {
            ForEach($lineItems) { $item in
                VStack(alignment: .leading, spacing: 8) {
                    TextField("Description", text: $item.description)
                    HStack(spacing: 12) {
                        TextField("Qty", text: $item.quantity)
                            .keyboardType(.decimalPad)
                            .frame(width: 60)
                        TextField("Unit Price", text: $item.unitPrice)
                            .keyboardType(.decimalPad)
                        if item.computedTotal > 0 {
                            Text(item.computedTotal, format: .currency(code: currency))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .frame(minWidth: 70, alignment: .trailing)
                        }
                    }
                }
                .padding(.vertical, 4)
            }
            .onDelete { lineItems.remove(atOffsets: $0) }

            Button {
                lineItems.append(DraftLineItem())
            } label: {
                Label("Add Line Item", systemImage: "plus.circle")
            }
        } header: {
            Text("Line Items")
        } footer: {
            if lineItems.count > 1 {
                Text("Swipe left on a line item to remove it.")
            }
        }
    }

    private var invoiceDetailsSection: some View {
        Section("Invoice Details") {
            TextField("Invoice Name (optional)", text: $invoiceName)

            Picker("Currency", selection: $currency) {
                Text("USD ($)").tag("USD")
                Text("EUR (€)").tag("EUR")
                Text("GBP (£)").tag("GBP")
                Text("CAD (C$)").tag("CAD")
                Text("AUD (A$)").tag("AUD")
            }

            Picker("Payment Terms", selection: $paymentTerms) {
                Text("Due on Receipt").tag("due_on_receipt")
                Text("Net 15").tag("net_15")
                Text("Net 30").tag("net_30")
                Text("Net 45").tag("net_45")
                Text("Net 60").tag("net_60")
            }

            Picker("Template", selection: $templateStyle) {
                Text("Clean Slate").tag("clean_slate")
                Text("Classic Professional").tag("classic_professional")
                Text("Executive").tag("executive")
                Text("Bold Modern").tag("bold_modern")
                Text("Neon Edge").tag("neon_edge")
            }

            HStack {
                Text("Tax Rate (%)")
                Spacer()
                TextField("0", text: $taxRate)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 80)
            }

            HStack {
                Text("Discount")
                Spacer()
                TextField("0.00", text: $discountAmount)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 100)
            }
        }
    }

    private var notesSection: some View {
        Section("Notes") {
            TextEditor(text: $notes)
                .frame(minHeight: 80)
        }
    }

    private var summarySection: some View {
        Section("Summary") {
            LabeledContent("Subtotal", value: computedSubtotal, format: .currency(code: currency))
            if computedTax > 0 {
                LabeledContent("Tax", value: computedTax, format: .currency(code: currency))
            }
            if computedDiscount > 0 {
                LabeledContent("Discount", value: computedDiscount, format: .currency(code: currency))
            }
            LabeledContent("Total", value: computedTotal, format: .currency(code: currency))
                .fontWeight(.semibold)
        }
    }

    // MARK: - Save

    struct RecurringRequest: Encodable {
        let clientName: String
        let clientEmail: String
        let clientPhone: String?
        let clientAddress: String?
        let invoiceName: String?
        let currency: String
        let taxRate: String?
        let discountAmount: String?
        let notes: String?
        let defaultPaymentTerms: String
        let templateStyle: String
        let frequency: String
        let startDate: String
        let endDate: String?
        let lineItems: [LineItemRequest]
    }

    @MainActor
    private func save() async {
        isSaving = true
        defer { isSaving = false }

        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withFullDate]

        let body = RecurringRequest(
            clientName: clientName,
            clientEmail: clientEmail,
            clientPhone: clientPhone.isEmpty ? nil : clientPhone,
            clientAddress: clientAddress.isEmpty ? nil : clientAddress,
            invoiceName: invoiceName.isEmpty ? nil : invoiceName,
            currency: currency,
            taxRate: taxRate.isEmpty ? nil : taxRate,
            discountAmount: discountAmount.isEmpty ? nil : discountAmount,
            notes: notes.isEmpty ? nil : notes,
            defaultPaymentTerms: paymentTerms,
            templateStyle: templateStyle,
            frequency: frequency.rawValue,
            startDate: iso.string(from: startDate),
            endDate: hasEndDate ? iso.string(from: endDate) : nil,
            lineItems: lineItems
                .filter { !$0.description.isEmpty }
                .map { LineItemRequest(description: $0.description, quantity: $0.quantity, unitPrice: $0.unitPrice) }
        )

        do {
            if let existing {
                let _: RecurringInvoiceResponse = try await appState.api.put("recurring/\(existing.id)/", body: body)
            } else {
                let _: RecurringInvoiceResponse = try await appState.api.post("recurring/", body: body)
            }
            onSave()
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Preview

#Preview {
    RecurringFormView(existing: nil) {}
        .environment(AppState())
}
