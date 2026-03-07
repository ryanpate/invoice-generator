import SwiftUI

// MARK: - AI Response Models

private struct AIGenerateResponse: Decodable {
    let lineItems: [AILineItem]
    let generationsRemaining: Int?

    struct AILineItem: Decodable {
        let description: String
        let quantity: String
        let unitPrice: String
    }
}

// MARK: - View

struct AIGenerateSection: View {
    /// Called when the user taps "Add All to Invoice" with the generated line items.
    let onAddItems: ([LineItemRequest]) -> Void

    /// Called when voice transcription extracts client fields the parent form may want to fill.
    var onVoiceResult: ((VoiceResult) -> Void)?

    @Environment(AppState.self) private var appState

    @State private var isExpanded: Bool = false
    @State private var description: String = ""
    @State private var isGenerating: Bool = false
    @State private var generatedItems: [LineItemRequest] = []
    @State private var generationsRemaining: Int? = nil
    @State private var errorMessage: String?
    @State private var showError: Bool = false

    var body: some View {
        DisclosureGroup(isExpanded: $isExpanded) {
            contentBody
                .padding(.top, 12)
        } label: {
            aiSectionHeader
        }
        .alert("Generation Failed", isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "Something went wrong. Please try again.")
        }
    }

    // MARK: - Header

    private var aiSectionHeader: some View {
        HStack(spacing: 8) {
            LinearGradient(
                colors: [.purple, Color(red: 0.6, green: 0.2, blue: 1.0)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .mask(
                Image(systemName: "sparkles")
                    .font(.system(size: 15, weight: .semibold))
            )
            .frame(width: 18, height: 18)

            Text("AI Generate")
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundStyle(
                    LinearGradient(
                        colors: [.purple, Color(red: 0.6, green: 0.2, blue: 1.0)],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )

            Text("BETA")
                .font(.system(size: 9, weight: .bold))
                .foregroundStyle(.white)
                .padding(.horizontal, 5)
                .padding(.vertical, 2)
                .background(
                    LinearGradient(
                        colors: [.purple, Color(red: 0.6, green: 0.2, blue: 1.0)],
                        startPoint: .leading,
                        endPoint: .trailing
                    ),
                    in: Capsule()
                )

            Spacer()

            if let remaining = generationsRemaining {
                Text("\(remaining) left")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - Content

    private var contentBody: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Description input
            ZStack(alignment: .topLeading) {
                if description.isEmpty {
                    Text("Describe your work, e.g., 'Built React dashboard, 12 hours at $150/hr'")
                        .font(.subheadline)
                        .foregroundStyle(Color(.placeholderText))
                        .padding(.horizontal, 4)
                        .padding(.vertical, 8)
                        .allowsHitTesting(false)
                }
                TextEditor(text: $description)
                    .font(.subheadline)
                    .frame(minHeight: 80)
                    .scrollContentBackground(.hidden)
            }
            .padding(10)
            .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 10))

            // Voice recording section
            VoiceRecordingView { result in
                handleVoiceResult(result)
            }
            .environment(appState)

            // Generate button
            Button(action: generate) {
                Group {
                    if isGenerating {
                        HStack(spacing: 8) {
                            ProgressView()
                                .progressViewStyle(.circular)
                                .scaleEffect(0.75)
                                .tint(.white)
                            Text("Generating...")
                                .font(.subheadline)
                                .fontWeight(.semibold)
                        }
                    } else {
                        HStack(spacing: 6) {
                            Image(systemName: "sparkles")
                                .font(.system(size: 13, weight: .semibold))
                            Text("Generate Line Items")
                                .font(.subheadline)
                                .fontWeight(.semibold)
                        }
                    }
                }
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity, minHeight: 40)
                .background(generateButtonBackground, in: RoundedRectangle(cornerRadius: 10))
            }
            .disabled(isGenerating || description.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

            // Generated items preview
            if !generatedItems.isEmpty {
                generatedItemsPreview
            }
        }
    }

    private var generateButtonBackground: some ShapeStyle {
        if isGenerating || description.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return AnyShapeStyle(Color(.systemGray3))
        }
        return AnyShapeStyle(
            LinearGradient(
                colors: [.purple, Color(red: 0.6, green: 0.2, blue: 1.0)],
                startPoint: .leading,
                endPoint: .trailing
            )
        )
    }

    // MARK: - Generated Items Preview

    private var generatedItemsPreview: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Generated Items")
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundStyle(.secondary)

            VStack(spacing: 0) {
                ForEach(Array(generatedItems.enumerated()), id: \.offset) { index, item in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(item.description)
                            .font(.subheadline)
                            .foregroundStyle(.primary)
                            .lineLimit(2)

                        HStack {
                            Text("Qty: \(item.quantity)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text("·")
                                .foregroundStyle(.secondary)
                            Text("$\(item.unitPrice)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .monospacedDigit()
                        }
                    }
                    .padding(.vertical, 8)
                    .padding(.horizontal, 12)
                    .frame(maxWidth: .infinity, alignment: .leading)

                    if index < generatedItems.count - 1 {
                        Divider()
                            .padding(.leading, 12)
                    }
                }
            }
            .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 10))

            Button {
                HapticManager.notification(.success)
                onAddItems(generatedItems)
                generatedItems = []
                description = ""
                withAnimation { isExpanded = false }
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "plus.circle.fill")
                        .font(.system(size: 15, weight: .semibold))
                    Text("Add All to Invoice")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                .foregroundStyle(.purple)
                .frame(maxWidth: .infinity, minHeight: 40)
                .background(
                    Color.purple.opacity(0.1),
                    in: RoundedRectangle(cornerRadius: 10)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.purple.opacity(0.3), lineWidth: 1)
                )
            }
        }
    }

    // MARK: - Actions

    private func generate() {
        let trimmed = description.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        isGenerating = true
        generatedItems = []
        HapticManager.impact(.medium)

        Task {
            do {
                struct GenerateRequest: Encodable { let description: String }
                let response: AIGenerateResponse = try await appState.api.post(
                    "ai/generate/",
                    body: GenerateRequest(description: trimmed)
                )
                await MainActor.run {
                    generatedItems = response.lineItems.map {
                        LineItemRequest(
                            description: $0.description,
                            quantity: $0.quantity,
                            unitPrice: $0.unitPrice
                        )
                    }
                    generationsRemaining = response.generationsRemaining
                    isGenerating = false
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showError = true
                    isGenerating = false
                }
            }
        }
    }

    private func handleVoiceResult(_ result: VoiceResult) {
        // Forward extracted client fields to the parent form
        onVoiceResult?(result)

        // Pre-fill the description textarea with the transcript so the user
        // can optionally re-run text-based generation if needed.
        if description.isEmpty {
            description = result.transcript
        }

        // Merge the voice line items into the generated preview and let the
        // user confirm before adding them — same UX as text generation.
        if !result.lineItems.isEmpty {
            generatedItems = result.lineItems
        }
    }
}

// MARK: - Preview

#Preview {
    ScrollView {
        Form {
            Section {
                AIGenerateSection(
                    onAddItems: { items in print("Add:", items) },
                    onVoiceResult: { result in print("Voice result:", result) }
                )
            }
        }
    }
    .environment(AppState())
}
