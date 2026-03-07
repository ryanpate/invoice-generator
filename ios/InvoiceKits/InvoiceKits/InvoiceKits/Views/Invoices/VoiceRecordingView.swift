import AVFoundation
import SwiftUI

// MARK: - Result Model

struct VoiceResult {
    var clientName: String?
    var clientEmail: String?
    var lineItems: [LineItemRequest]
    var transcript: String
}

// MARK: - Voice Response from API

private struct VoiceGenerateResponse: Decodable {
    let transcript: String
    let clientName: String?
    let clientEmail: String?
    let lineItems: [VoiceLineItem]

    struct VoiceLineItem: Decodable {
        let description: String
        let quantity: String
        let unitPrice: String
    }
}

// MARK: - Recording State

private enum RecordingState {
    case idle
    case recording
    case processing
    case result(transcript: String, clientName: String?, clientEmail: String?, lineItems: [LineItemRequest])
    case failed(String)
}

// MARK: - View

struct VoiceRecordingView: View {
    let onApply: (VoiceResult) -> Void

    @Environment(AppState.self) private var appState

    @State private var recordingState: RecordingState = .idle
    @State private var recorder: AVAudioRecorder?
    @State private var recordingURL: URL?
    @State private var elapsedSeconds: Int = 0
    @State private var autoStopTask: Task<Void, Never>?
    @State private var tickTask: Task<Void, Never>?

    private let maxSeconds = 60

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            switch recordingState {
            case .idle:
                idleView

            case .recording:
                recordingView

            case .processing:
                processingView

            case .result(let transcript, let clientName, let clientEmail, let lineItems):
                resultView(
                    transcript: transcript,
                    clientName: clientName,
                    clientEmail: clientEmail,
                    lineItems: lineItems
                )

            case .failed(let message):
                failedView(message: message)
            }
        }
    }

    // MARK: - Idle

    private var idleView: some View {
        Button {
            startRecording()
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "mic.fill")
                    .font(.system(size: 14, weight: .semibold))
                Text("Dictate invoice details")
                    .font(.subheadline)
                    .fontWeight(.medium)
            }
            .foregroundStyle(.purple)
        }
    }

    // MARK: - Recording

    private var recordingView: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                // Pulsing red indicator
                PulsingDot()

                TimelineView(.periodic(from: .now, by: 1)) { _ in
                    Text(formattedTime(elapsedSeconds))
                        .font(.system(.subheadline, design: .monospaced))
                        .fontWeight(.semibold)
                        .foregroundStyle(.primary)
                        .contentTransition(.numericText())
                }

                Text("Recording...")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                Spacer()

                Button {
                    stopRecording()
                } label: {
                    Label("Stop", systemImage: "stop.fill")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(.red, in: Capsule())
                }
            }

            if elapsedSeconds >= 55 {
                Text("Recording will stop in \(maxSeconds - elapsedSeconds)s")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.2), value: elapsedSeconds >= 55)
    }

    // MARK: - Processing

    private var processingView: some View {
        HStack(spacing: 10) {
            ProgressView()
                .progressViewStyle(.circular)
                .scaleEffect(0.8)
            Text("Transcribing & parsing...")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Result

    private func resultView(
        transcript: String,
        clientName: String?,
        clientEmail: String?,
        lineItems: [LineItemRequest]
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // Transcript preview
            VStack(alignment: .leading, spacing: 4) {
                Label("Transcript", systemImage: "text.quote")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundStyle(.secondary)

                Text(transcript)
                    .font(.caption)
                    .foregroundStyle(.primary)
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 8))
            }

            // Extracted fields
            if clientName != nil || clientEmail != nil {
                VStack(alignment: .leading, spacing: 4) {
                    Label("Extracted Fields", systemImage: "person.fill")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(.secondary)

                    VStack(alignment: .leading, spacing: 2) {
                        if let name = clientName {
                            Text("Client: \(name)")
                                .font(.caption)
                                .foregroundStyle(.primary)
                        }
                        if let email = clientEmail {
                            Text("Email: \(email)")
                                .font(.caption)
                                .foregroundStyle(.primary)
                        }
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 8))
                }
            }

            // Line items preview
            if !lineItems.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Label("\(lineItems.count) Line Item\(lineItems.count == 1 ? "" : "s")", systemImage: "list.bullet")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(.secondary)

                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(lineItems.enumerated()), id: \.offset) { _, item in
                            HStack {
                                Text(item.description)
                                    .font(.caption)
                                    .foregroundStyle(.primary)
                                    .lineLimit(1)
                                Spacer()
                                Text("\(item.quantity) x $\(item.unitPrice)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                    .monospacedDigit()
                            }
                        }
                    }
                    .padding(10)
                    .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 8))
                }
            }

            // Actions
            HStack(spacing: 10) {
                Button {
                    recordingState = .idle
                    elapsedSeconds = 0
                } label: {
                    Text("Discard")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, minHeight: 36)
                        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 8))
                }

                Button {
                    let result = VoiceResult(
                        clientName: clientName,
                        clientEmail: clientEmail,
                        lineItems: lineItems,
                        transcript: transcript
                    )
                    onApply(result)
                    recordingState = .idle
                    elapsedSeconds = 0
                } label: {
                    Text("Apply to Invoice")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity, minHeight: 36)
                        .background(.purple, in: RoundedRectangle(cornerRadius: 8))
                }
                .disabled(lineItems.isEmpty)
            }
        }
    }

    // MARK: - Failed

    private func failedView(message: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(message, systemImage: "exclamationmark.triangle.fill")
                .font(.caption)
                .foregroundStyle(.red)

            Button {
                recordingState = .idle
                elapsedSeconds = 0
            } label: {
                Text("Try Again")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundStyle(.purple)
            }
        }
    }

    // MARK: - Recording Logic

    private func startRecording() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.record, mode: .default)
            try session.setActive(true)
        } catch {
            recordingState = .failed("Microphone unavailable.")
            return
        }

        let tmpURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("m4a")
        recordingURL = tmpURL

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]

        do {
            recorder = try AVAudioRecorder(url: tmpURL, settings: settings)
            recorder?.record()
        } catch {
            recordingState = .failed("Could not start recording.")
            return
        }

        elapsedSeconds = 0
        recordingState = .recording
        startTicker()

        // Auto-stop at 60 seconds
        autoStopTask = Task {
            try? await Task.sleep(for: .seconds(maxSeconds))
            guard !Task.isCancelled else { return }
            await MainActor.run { stopRecording() }
        }
    }

    private func stopRecording() {
        autoStopTask?.cancel()
        tickTask?.cancel()
        recorder?.stop()
        recorder = nil
        try? AVAudioSession.sharedInstance().setActive(false)

        guard let url = recordingURL else {
            recordingState = .failed("No audio recorded.")
            return
        }
        recordingState = .processing
        Task { await uploadAudio(from: url) }
    }

    private func startTicker() {
        tickTask?.cancel()
        tickTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(1))
                guard !Task.isCancelled else { break }
                await MainActor.run { elapsedSeconds += 1 }
            }
        }
    }

    // MARK: - Upload

    @MainActor
    private func uploadAudio(from url: URL) async {
        do {
            let audioData = try Data(contentsOf: url)
            try? FileManager.default.removeItem(at: url)

            let response: VoiceGenerateResponse = try await appState.api.upload(
                "ai/voice-generate/",
                fileData: audioData,
                filename: "voice.m4a",
                mimeType: "audio/mp4"
            )

            let items = response.lineItems.map {
                LineItemRequest(
                    description: $0.description,
                    quantity: $0.quantity,
                    unitPrice: $0.unitPrice
                )
            }

            recordingState = .result(
                transcript: response.transcript,
                clientName: response.clientName,
                clientEmail: response.clientEmail,
                lineItems: items
            )
        } catch {
            recordingState = .failed("Transcription failed. Please try again.")
        }
    }

    // MARK: - Helpers

    private func formattedTime(_ seconds: Int) -> String {
        String(format: "%d:%02d", seconds / 60, seconds % 60)
    }
}

// MARK: - Pulsing Dot

private struct PulsingDot: View {
    @State private var pulsing = false

    var body: some View {
        Circle()
            .fill(.red)
            .frame(width: 10, height: 10)
            .scaleEffect(pulsing ? 1.4 : 1.0)
            .opacity(pulsing ? 0.5 : 1.0)
            .animation(.easeInOut(duration: 0.7).repeatForever(autoreverses: true), value: pulsing)
            .onAppear { pulsing = true }
    }
}

// MARK: - Preview

#Preview {
    VStack(alignment: .leading, spacing: 20) {
        VoiceRecordingView { result in
            print("Applied:", result)
        }
    }
    .padding()
    .environment(AppState())
}
