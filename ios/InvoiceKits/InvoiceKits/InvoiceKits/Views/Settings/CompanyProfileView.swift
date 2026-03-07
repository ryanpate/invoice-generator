import SwiftUI
import PhotosUI

struct CompanyProfileView: View {
    @Environment(AppState.self) private var appState

    // MARK: - Form Fields

    @State private var name = ""
    @State private var email = ""
    @State private var phone = ""
    @State private var address = ""
    @State private var city = ""
    @State private var state = ""
    @State private var zipCode = ""
    @State private var country = ""
    @State private var website = ""
    @State private var taxId = ""
    @State private var defaultPaymentTerms = "net_30"
    @State private var defaultNotes = ""

    // MARK: - Logo / Signature

    @State private var logoItem: PhotosPickerItem?
    @State private var logoImageData: Data?
    @State private var logoPreviewImage: Image?
    @State private var existingLogoUrl: String?

    @State private var signatureItem: PhotosPickerItem?
    @State private var signatureImageData: Data?
    @State private var signaturePreviewImage: Image?
    @State private var existingSignatureUrl: String?

    // MARK: - UI State

    @State private var isLoading = false
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var showSuccessBanner = false

    var body: some View {
        Form {
            if isLoading {
                Section {
                    HStack {
                        Spacer()
                        ProgressView()
                        Spacer()
                    }
                }
            }

            companyInfoSection
            addressSection
            paymentDefaultsSection
            logoSection
            signatureSection
        }
        .navigationTitle("Company Profile")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Save") {
                    Task { await save() }
                }
                .disabled(isSaving || name.isEmpty)
                .overlay {
                    if isSaving { ProgressView().scaleEffect(0.7) }
                }
            }
        }
        .task { await load() }
        .onChange(of: logoItem) { Task { await loadLogoImage() } }
        .onChange(of: signatureItem) { Task { await loadSignatureImage() } }
        .overlay(alignment: .top) {
            if showSuccessBanner {
                successBanner
            }
        }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: {
            if let msg = errorMessage { Text(msg) }
        }
    }

    // MARK: - Sections

    private var companyInfoSection: some View {
        Section("Company Information") {
            TextField("Company Name *", text: $name)
                .autocorrectionDisabled()
            TextField("Email", text: $email)
                .textContentType(.emailAddress)
                .keyboardType(.emailAddress)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
            TextField("Phone", text: $phone)
                .textContentType(.telephoneNumber)
                .keyboardType(.phonePad)
            TextField("Website", text: $website)
                .textContentType(.URL)
                .keyboardType(.URL)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
            TextField("Tax ID / EIN", text: $taxId)
                .autocorrectionDisabled()
        }
    }

    private var addressSection: some View {
        Section("Address") {
            TextField("Street Address", text: $address)
                .textContentType(.streetAddressLine1)
            TextField("City", text: $city)
                .textContentType(.addressCity)
            TextField("State / Province", text: $state)
                .textContentType(.addressState)
            TextField("ZIP / Postal Code", text: $zipCode)
                .textContentType(.postalCode)
                .keyboardType(.asciiCapable)
            TextField("Country", text: $country)
                .textContentType(.countryName)
        }
    }

    private var paymentDefaultsSection: some View {
        Section("Invoice Defaults") {
            Picker("Default Payment Terms", selection: $defaultPaymentTerms) {
                Text("Due on Receipt").tag("due_on_receipt")
                Text("Net 15").tag("net_15")
                Text("Net 30").tag("net_30")
                Text("Net 45").tag("net_45")
                Text("Net 60").tag("net_60")
            }

            VStack(alignment: .leading, spacing: 4) {
                Text("Default Notes")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                TextEditor(text: $defaultNotes)
                    .frame(minHeight: 80)
            }
        }
    }

    private var logoSection: some View {
        Section {
            if let preview = logoPreviewImage {
                HStack {
                    Spacer()
                    preview
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: 200, maxHeight: 100)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    Spacer()
                }
            } else if let urlString = existingLogoUrl, let url = URL(string: urlString) {
                HStack {
                    Spacer()
                    AsyncImage(url: url) { image in
                        image
                            .resizable()
                            .scaledToFit()
                            .frame(maxWidth: 200, maxHeight: 100)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    } placeholder: {
                        ProgressView()
                    }
                    Spacer()
                }
            }

            PhotosPicker(selection: $logoItem, matching: .images) {
                Label(
                    existingLogoUrl != nil || logoPreviewImage != nil ? "Change Logo" : "Upload Logo",
                    systemImage: "photo.badge.plus"
                )
            }
        } header: {
            Text("Company Logo")
        } footer: {
            Text("PNG or JPEG, appears on all invoices.")
        }
    }

    private var signatureSection: some View {
        Section {
            if let preview = signaturePreviewImage {
                HStack {
                    Spacer()
                    preview
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: 240, maxHeight: 80)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                    Spacer()
                }
            } else if let urlString = existingSignatureUrl, let url = URL(string: urlString) {
                HStack {
                    Spacer()
                    AsyncImage(url: url) { image in
                        image
                            .resizable()
                            .scaledToFit()
                            .frame(maxWidth: 240, maxHeight: 80)
                    } placeholder: {
                        ProgressView()
                    }
                    Spacer()
                }
            }

            PhotosPicker(selection: $signatureItem, matching: .images) {
                Label(
                    existingSignatureUrl != nil || signaturePreviewImage != nil ? "Change Signature" : "Upload Signature",
                    systemImage: "signature"
                )
            }
        } header: {
            Text("Digital Signature")
        } footer: {
            Text("Appears at the bottom of invoice PDFs.")
        }
    }

    private var successBanner: some View {
        Text("Profile saved successfully.")
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

    // MARK: - Image Loading

    private func loadLogoImage() async {
        guard let item = logoItem,
              let data = try? await item.loadTransferable(type: Data.self),
              let uiImage = UIImage(data: data) else { return }
        logoImageData = data
        logoPreviewImage = Image(uiImage: uiImage)
    }

    private func loadSignatureImage() async {
        guard let item = signatureItem,
              let data = try? await item.loadTransferable(type: Data.self),
              let uiImage = UIImage(data: data) else { return }
        signatureImageData = data
        signaturePreviewImage = Image(uiImage: uiImage)
    }

    // MARK: - Data

    @MainActor
    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let company: CompanyResponse = try await appState.api.get("company/")
            name                = company.name
            email               = company.email ?? ""
            phone               = company.phone ?? ""
            address             = company.address ?? ""
            city                = company.city ?? ""
            state               = company.state ?? ""
            zipCode             = company.zipCode ?? ""
            country             = company.country ?? ""
            website             = company.website ?? ""
            taxId               = company.taxId ?? ""
            defaultPaymentTerms = company.defaultPaymentTerms ?? "net_30"
            defaultNotes        = company.defaultNotes ?? ""
            existingLogoUrl     = company.logoUrl
            existingSignatureUrl = company.signatureUrl
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    struct CompanyUpdateRequest: Encodable {
        let name: String
        let email: String?
        let phone: String?
        let address: String?
        let city: String?
        let state: String?
        let zipCode: String?
        let country: String?
        let website: String?
        let taxId: String?
        let defaultPaymentTerms: String?
        let defaultNotes: String?
    }

    @MainActor
    private func save() async {
        isSaving = true
        defer { isSaving = false }

        do {
            let body = CompanyUpdateRequest(
                name: name,
                email: email.isEmpty ? nil : email,
                phone: phone.isEmpty ? nil : phone,
                address: address.isEmpty ? nil : address,
                city: city.isEmpty ? nil : city,
                state: state.isEmpty ? nil : state,
                zipCode: zipCode.isEmpty ? nil : zipCode,
                country: country.isEmpty ? nil : country,
                website: website.isEmpty ? nil : website,
                taxId: taxId.isEmpty ? nil : taxId,
                defaultPaymentTerms: defaultPaymentTerms,
                defaultNotes: defaultNotes.isEmpty ? nil : defaultNotes
            )
            let _: CompanyResponse = try await appState.api.put("company/", body: body)

            // Upload logo if changed
            if let data = logoImageData {
                let _: CompanyResponse = try await appState.api.upload(
                    "company/logo/",
                    fileData: data,
                    filename: "logo.jpg",
                    mimeType: "image/jpeg"
                )
                logoImageData = nil
            }

            // Upload signature if changed
            if let data = signatureImageData {
                let _: CompanyResponse = try await appState.api.upload(
                    "company/signature/",
                    fileData: data,
                    filename: "signature.jpg",
                    mimeType: "image/jpeg"
                )
                signatureImageData = nil
            }

            withAnimation { showSuccessBanner = true }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        CompanyProfileView()
            .environment(AppState())
    }
}
