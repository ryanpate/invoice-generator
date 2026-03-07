import PDFKit
import SwiftUI

struct PDFPreviewView: View {
    let invoiceId: Int

    @Environment(AppState.self) private var appState

    @State private var pdfData: Data?
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var showShareSheet = false

    var body: some View {
        ZStack {
            if isLoading {
                ProgressView("Loading PDF…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let data = pdfData {
                PDFKitView(data: data)
                    .ignoresSafeArea(edges: .bottom)
            } else {
                ContentUnavailableView(
                    "Could Not Load PDF",
                    systemImage: "doc.slash",
                    description: Text(errorMessage ?? "An unexpected error occurred.")
                )
            }
        }
        .navigationTitle("Invoice PDF")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                if pdfData != nil {
                    Button {
                        showShareSheet = true
                    } label: {
                        Image(systemName: "square.and.arrow.up")
                    }
                    .accessibilityLabel("Share PDF")
                }
            }
        }
        .sheet(isPresented: $showShareSheet) {
            if let data = pdfData {
                ShareSheet(activityItems: [data])
                    .ignoresSafeArea()
            }
        }
        .task {
            await loadPDF()
        }
    }

    // MARK: - PDF Download

    private func loadPDF() async {
        isLoading = true
        errorMessage = nil
        do {
            let data = try await appState.api.getData("invoices/\(invoiceId)/pdf/")
            await MainActor.run {
                pdfData = data
                isLoading = false
            }
        } catch {
            await MainActor.run {
                errorMessage = error.localizedDescription
                isLoading = false
            }
        }
    }
}

// MARK: - PDFKit Wrapper

private struct PDFKitView: UIViewRepresentable {
    let data: Data

    func makeUIView(context: Context) -> PDFView {
        let pdfView = PDFView()
        pdfView.autoScales = true
        pdfView.displayMode = .singlePageContinuous
        pdfView.displayDirection = .vertical
        pdfView.document = PDFDocument(data: data)
        return pdfView
    }

    func updateUIView(_ uiView: PDFView, context: Context) {
        if uiView.document == nil {
            uiView.document = PDFDocument(data: data)
        }
    }
}

// MARK: - UIActivityViewController Wrapper

private struct ShareSheet: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

// MARK: - APIClient Extension

extension APIClient {
    /// Fetches raw `Data` from the given path, applying the Bearer token and handling 401 refresh.
    func getData(_ path: String) async throws -> Data {
        let url = Constants.apiBaseURL.appendingPathComponent(path)
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "GET"
        if let token = accessToken {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: urlRequest)
        let httpResponse = response as! HTTPURLResponse

        if httpResponse.statusCode == 401 {
            if try await refreshAccessTokenPublic() {
                return try await getData(path)
            }
            throw APIError.unauthorized
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode, data)
        }

        return data
    }

    // Calls the private refresh method via the public surface.
    // Because `refreshAccessToken()` is private, we expose a thin wrapper here.
    func refreshAccessTokenPublic() async throws -> Bool {
        // Trigger a dummy decode-typed request that will invoke the existing refresh
        // logic inside `request(_:path:body:queryItems:)`. Instead, we replicate the
        // minimal refresh call so we stay DRY without exposing private state.
        guard let refresh = refreshToken else { return false }

        struct RefreshBody: Encodable { let refresh: String }
        struct RefreshResponse: Decodable { let access: String }

        let decoder: JSONDecoder = {
            let d = JSONDecoder()
            d.keyDecodingStrategy = .convertFromSnakeCase
            return d
        }()
        let encoder: JSONEncoder = {
            let e = JSONEncoder()
            e.keyEncodingStrategy = .convertToSnakeCase
            return e
        }()

        var req = URLRequest(url: Constants.apiBaseURL.appendingPathComponent("auth/token/refresh/"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try encoder.encode(RefreshBody(refresh: refresh))

        let (data, response) = try await URLSession.shared.data(for: req)
        guard (response as! HTTPURLResponse).statusCode == 200 else {
            clearTokens()
            return false
        }

        let result = try decoder.decode(RefreshResponse.self, from: data)
        saveTokens(access: result.access, refresh: refresh)
        return true
    }
}

#Preview {
    NavigationStack {
        PDFPreviewView(invoiceId: 1)
            .environment(AppState())
    }
}
