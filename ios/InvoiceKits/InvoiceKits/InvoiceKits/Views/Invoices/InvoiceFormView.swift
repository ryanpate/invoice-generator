import SwiftUI

// MARK: - Request Body

private struct InvoiceRequest: Encodable {
    var clientName: String
    var clientEmail: String
    var clientPhone: String
    var clientAddress: String
    var invoiceDate: String
    var dueDate: String
    var paymentTerms: String
    var currency: String
    var taxRate: String
    var discountAmount: String
    var notes: String
    var templateStyle: String
    var lineItems: [LineItemRequest]
}

// MARK: - Editable Line Item

private struct EditableLineItem: Identifiable {
    let id = UUID()
    var description: String = ""
    var quantity: String = "1"
    var unitPrice: String = ""

    var lineTotal: Decimal {
        let q = Decimal(string: quantity) ?? 0
        let p = Decimal(string: unitPrice) ?? 0
        return q * p
    }
}

// MARK: - Form State

private enum PaymentTerms: String, CaseIterable {
    case net30       = "net_30"
    case net15       = "net_15"
    case net60       = "net_60"
    case dueOnReceipt = "due_on_receipt"

    var displayName: String {
        switch self {
        case .net30:        return "Net 30"
        case .net15:        return "Net 15"
        case .net60:        return "Net 60"
        case .dueOnReceipt: return "Due on Receipt"
        }
    }
}

private enum Currency: String, CaseIterable {
    case usd = "USD"
    case eur = "EUR"
    case gbp = "GBP"
    case cad = "CAD"
    case aud = "AUD"
}

private enum TemplateStyle: String, CaseIterable {
    case cleanSlate          = "clean_slate"
    case executive           = "executive"
    case boldModern          = "bold_modern"
    case classicProfessional = "classic_professional"
    case neonEdge            = "neon_edge"

    var displayName: String {
        switch self {
        case .cleanSlate:          return "Clean Slate"
        case .executive:           return "Executive"
        case .boldModern:          return "Bold Modern"
        case .classicProfessional: return "Classic Professional"
        case .neonEdge:            return "Neon Edge"
        }
    }
}

// MARK: - View

struct InvoiceFormView: View {
    /// Nil = create mode. Non-nil = edit mode with pre-populated fields.
    var invoice: InvoiceResponse?

    var onSuccess: ((InvoiceResponse) -> Void)?

    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    // MARK: Client Info
    @State private var clientName: String = ""
    @State private var clientEmail: String = ""
    @State private var clientPhone: String = ""
    @State private var clientAddress: String = ""

    // MARK: Line Items
    @State private var lineItems: [EditableLineItem] = [EditableLineItem()]

    // MARK: Financial
    @State private var currency: Currency = .usd
    @State private var taxRate: String = "0"
    @State private var discountAmount: String = "0"

    // MARK: Details
    @State private var invoiceDate: Date = .now
    @State private var dueDate: Date = Calendar.current.date(byAdding: .day, value: 30, to: .now) ?? .now
    @State private var paymentTerms: PaymentTerms = .net30
    @State private var templateStyle: TemplateStyle = .cleanSlate

    // MARK: Notes
    @State private var notes: String = ""

    // MARK: UI State
    @State private var isSaving: Bool = false
    @State private var errorMessage: String?
    @State private var showError: Bool = false

    private var isEditing: Bool { invoice != nil }

    // MARK: - Computed Totals

    private var subtotal: Decimal {
        lineItems.reduce(Decimal.zero) { $0 + $1.lineTotal }
    }

    private var taxDecimal: Decimal {
        Decimal(string: taxRate) ?? 0
    }

    private var discountDecimal: Decimal {
        Decimal(string: discountAmount) ?? 0
    }

    private var taxAmount: Decimal {
        subtotal * (taxDecimal / 100)
    }

    private var total: Decimal {
        subtotal + taxAmount - discountDecimal
    }

    // MARK: - Body

    var body: some View {
        Form {
            clientInfoSection
            lineItemsSection
            financialSection
            detailsSection
            notesSection
            aiGenerateSection
        }
        .navigationTitle(isEditing ? "Edit Invoice" : "New Invoice")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Cancel") { dismiss() }
            }
            ToolbarItem(placement: .confirmationAction) {
                saveButton
            }
        }
        .alert("Save Failed", isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "An unexpected error occurred.")
        }
        .onAppear(perform: populateIfEditing)
        .disabled(isSaving)
    }

    // MARK: - Sections

    private var clientInfoSection: some View {
        Section("Client Info") {
            TextField("Client Name", text: $clientName)
                .textContentType(.organizationName)
                .autocorrectionDisabled()

            VStack(alignment: .leading, spacing: 4) {
                TextField("Client Email", text: $clientEmail)
                    .textContentType(.emailAddress)
                    .keyboardType(.emailAddress)
                    .autocapitalization(.none)
                    .autocorrectionDisabled()

                ClientRatingBadge(email: clientEmail)
                    .environment(appState)
                    .padding(.top, 2)
            }

            TextField("Phone (optional)", text: $clientPhone)
                .textContentType(.telephoneNumber)
                .keyboardType(.phonePad)

            TextField("Address (optional)", text: $clientAddress, axis: .vertical)
                .lineLimit(2...4)
                .textContentType(.fullStreetAddress)
        }
    }

    private var lineItemsSection: some View {
        Section {
            ForEach($lineItems) { $item in
                LineItemRow(item: $item)
            }
            .onDelete { offsets in
                lineItems.remove(atOffsets: offsets)
            }

            Button {
                HapticManager.impact(.light)
                withAnimation { lineItems.append(EditableLineItem()) }
            } label: {
                Label("Add Line Item", systemImage: "plus.circle.fill")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundStyle(.blue)
            }
        } header: {
            Text("Line Items")
        }
    }

    private var financialSection: some View {
        Section("Financial") {
            Picker("Currency", selection: $currency) {
                ForEach(Currency.allCases, id: \.self) { c in
                    Text(c.rawValue).tag(c)
                }
            }

            LabeledContent {
                TextField("0", text: $taxRate)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
            } label: {
                Text("Tax Rate (%)")
            }

            LabeledContent {
                TextField("0.00", text: $discountAmount)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .monospacedDigit()
            } label: {
                Text("Discount")
            }

            totalsView
        }
    }

    private var totalsView: some View {
        VStack(spacing: 6) {
            totalRow(label: "Subtotal", value: subtotal, color: .primary)

            if taxDecimal > 0 {
                totalRow(label: "Tax (\(taxRate)%)", value: taxAmount, color: .secondary)
            }

            if discountDecimal > 0 {
                totalRow(label: "Discount", value: -discountDecimal, color: .green)
            }

            Divider()

            totalRow(label: "Total", value: total, color: .primary, font: .subheadline, weight: .bold)
        }
        .padding(.vertical, 4)
    }

    private func totalRow(
        label: String,
        value: Decimal,
        color: Color,
        font: Font = .subheadline,
        weight: Font.Weight = .regular
    ) -> some View {
        HStack {
            Text(label)
                .font(font)
                .fontWeight(weight)
                .foregroundStyle(color == .secondary ? Color.secondary : color)
            Spacer()
            Text(formatted(value))
                .font(font)
                .fontWeight(weight)
                .monospacedDigit()
                .foregroundStyle(color == .secondary ? Color.secondary : color)
        }
    }

    private var detailsSection: some View {
        Section("Details") {
            DatePicker("Invoice Date", selection: $invoiceDate, displayedComponents: .date)

            DatePicker("Due Date", selection: $dueDate, displayedComponents: .date)

            Picker("Payment Terms", selection: $paymentTerms) {
                ForEach(PaymentTerms.allCases, id: \.self) { term in
                    Text(term.displayName).tag(term)
                }
            }

            Picker("Template", selection: $templateStyle) {
                ForEach(TemplateStyle.allCases, id: \.self) { style in
                    Text(style.displayName).tag(style)
                }
            }
        }
    }

    private var notesSection: some View {
        Section("Notes") {
            ZStack(alignment: .topLeading) {
                if notes.isEmpty {
                    Text("Payment instructions, thank-you message…")
                        .font(.subheadline)
                        .foregroundStyle(Color(.placeholderText))
                        .padding(.top, 8)
                        .allowsHitTesting(false)
                }
                TextEditor(text: $notes)
                    .frame(minHeight: 80)
                    .scrollContentBackground(.hidden)
            }
        }
    }

    private var aiGenerateSection: some View {
        Section {
            AIGenerateSection(
                onAddItems: { requests in
                    let newItems = requests.map { req in
                        EditableLineItem(
                            description: req.description,
                            quantity: req.quantity,
                            unitPrice: req.unitPrice
                        )
                    }
                    withAnimation {
                        // Replace the placeholder empty item if it's the only one and still blank.
                        if lineItems.count == 1,
                           lineItems[0].description.isEmpty,
                           lineItems[0].unitPrice.isEmpty {
                            lineItems = newItems
                        } else {
                            lineItems.append(contentsOf: newItems)
                        }
                    }
                },
                onVoiceResult: { result in
                    applyVoiceResult(result)
                }
            )
            .environment(appState)
        }
    }

    // MARK: - Save Button

    private var saveButton: some View {
        Group {
            if isSaving {
                ProgressView()
                    .progressViewStyle(.circular)
            } else {
                Button(isEditing ? "Update" : "Create") {
                    Task { await save() }
                }
                .fontWeight(.semibold)
                .disabled(!isFormValid)
            }
        }
    }

    private var isFormValid: Bool {
        !clientName.trimmingCharacters(in: .whitespaces).isEmpty &&
        !lineItems.isEmpty &&
        lineItems.allSatisfy { !$0.description.isEmpty }
    }

    // MARK: - Populate for Edit

    private func populateIfEditing() {
        guard let invoice else { return }

        clientName = invoice.clientName
        clientEmail = invoice.clientEmail
        clientPhone = invoice.clientPhone ?? ""
        clientAddress = invoice.clientAddress ?? ""
        notes = invoice.notes ?? ""
        taxRate = invoice.taxRate
        discountAmount = invoice.discountAmount

        currency = Currency(rawValue: invoice.currency) ?? .usd
        paymentTerms = PaymentTerms(rawValue: invoice.paymentTerms) ?? .net30
        templateStyle = TemplateStyle(rawValue: invoice.templateStyle) ?? .cleanSlate

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        if let d = formatter.date(from: invoice.invoiceDate) { invoiceDate = d }
        if let d = formatter.date(from: invoice.dueDate) { dueDate = d }

        if let items = invoice.lineItems, !items.isEmpty {
            lineItems = items.map { item in
                EditableLineItem(
                    description: item.description,
                    quantity: item.quantity,
                    unitPrice: item.unitPrice
                )
            }
        }
    }

    // MARK: - Voice Apply

    private func applyVoiceResult(_ result: VoiceResult) {
        if clientName.isEmpty, let name = result.clientName { clientName = name }
        if clientEmail.isEmpty, let email = result.clientEmail { clientEmail = email }

        if !result.lineItems.isEmpty {
            let newItems = result.lineItems.map { req in
                EditableLineItem(
                    description: req.description,
                    quantity: req.quantity,
                    unitPrice: req.unitPrice
                )
            }
            withAnimation {
                if lineItems.count == 1,
                   lineItems[0].description.isEmpty,
                   lineItems[0].unitPrice.isEmpty {
                    lineItems = newItems
                } else {
                    lineItems.append(contentsOf: newItems)
                }
            }
        }
    }

    // MARK: - Save

    @MainActor
    private func save() async {
        guard isFormValid else { return }
        isSaving = true

        let dateFormatter = ISO8601DateFormatter()
        dateFormatter.formatOptions = [.withFullDate]

        let body = InvoiceRequest(
            clientName: clientName.trimmingCharacters(in: .whitespaces),
            clientEmail: clientEmail.trimmingCharacters(in: .whitespaces),
            clientPhone: clientPhone.trimmingCharacters(in: .whitespaces),
            clientAddress: clientAddress.trimmingCharacters(in: .whitespaces),
            invoiceDate: dateFormatter.string(from: invoiceDate),
            dueDate: dateFormatter.string(from: dueDate),
            paymentTerms: paymentTerms.rawValue,
            currency: currency.rawValue,
            taxRate: taxRate,
            discountAmount: discountAmount,
            notes: notes.trimmingCharacters(in: .whitespacesAndNewlines),
            templateStyle: templateStyle.rawValue,
            lineItems: lineItems.map {
                LineItemRequest(description: $0.description, quantity: $0.quantity, unitPrice: $0.unitPrice)
            }
        )

        do {
            let response: InvoiceResponse
            if let existing = invoice {
                response = try await appState.api.put("invoices/\(existing.id)/", body: body)
            } else {
                response = try await appState.api.post("invoices/", body: body)
            }
            HapticManager.notification(.success)
            onSuccess?(response)
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        isSaving = false
    }

    // MARK: - Helpers

    private func formatted(_ value: Decimal) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.minimumFractionDigits = 2
        formatter.maximumFractionDigits = 2
        return formatter.string(from: value as NSDecimalNumber) ?? "0.00"
    }
}

// MARK: - Line Item Row

private struct LineItemRow: View {
    @Binding var item: EditableLineItem

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            TextField("Description", text: $item.description)
                .font(.subheadline)

            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Qty")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    TextField("1", text: $item.quantity)
                        .keyboardType(.decimalPad)
                        .font(.subheadline)
                        .monospacedDigit()
                        .frame(maxWidth: 60)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("Unit Price")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    TextField("0.00", text: $item.unitPrice)
                        .keyboardType(.decimalPad)
                        .font(.subheadline)
                        .monospacedDigit()
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 2) {
                    Text("Total")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text(lineTotalFormatted)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .monospacedDigit()
                        .foregroundStyle(.primary)
                }
            }
        }
        .padding(.vertical, 4)
    }

    private var lineTotalFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.minimumFractionDigits = 2
        formatter.maximumFractionDigits = 2
        return formatter.string(from: item.lineTotal as NSDecimalNumber) ?? "0.00"
    }
}

// MARK: - Previews

#Preview("Create") {
    NavigationStack {
        InvoiceFormView()
    }
    .environment(AppState())
}

#Preview("Edit") {
    let sample = InvoiceResponse(
        id: 1,
        invoiceNumber: "INV-001",
        invoiceName: "Sample Invoice",
        status: "draft",
        clientName: "Acme Corp",
        clientEmail: "billing@acme.com",
        clientPhone: "+1 555 0100",
        clientAddress: "123 Main St, Springfield",
        invoiceDate: "2026-03-01",
        dueDate: "2026-03-31",
        paymentTerms: "net_30",
        currency: "USD",
        currencySymbol: "$",
        subtotal: "1500.00",
        taxRate: "10",
        taxAmount: "150.00",
        discountAmount: "0",
        total: "1650.00",
        notes: "Thank you for your business.",
        templateStyle: "clean_slate",
        lineItems: [
            LineItemResponse(id: 1, description: "Web Design", quantity: "10", unitPrice: "150.00", total: "1500.00")
        ],
        remindersPaused: false,
        lateFeesPaused: false,
        lateFeeApplied: nil,
        paidAt: nil,
        sentAt: nil,
        createdAt: "2026-03-01T00:00:00Z",
        updatedAt: "2026-03-01T00:00:00Z"
    )

    NavigationStack {
        InvoiceFormView(invoice: sample)
    }
    .environment(AppState())
}
