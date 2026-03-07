import SwiftUI

struct TimerCardView: View {
    @Environment(AppState.self) private var appState

    // Live timer state
    @State private var activeTimer: ActiveTimerResponse?
    @State private var isLoadingStatus = true

    // Start-timer form
    @State private var showStartForm = false
    @State private var newDescription = ""
    @State private var newClientName = ""
    @State private var newClientEmail = ""
    @State private var newHourlyRate = ""

    // Async state
    @State private var isActing = false
    @State private var errorMessage: String?
    @State private var showDiscardConfirm = false

    // Callback so parent list can reload after a stop
    var onTimerStopped: (() -> Void)?

    var body: some View {
        VStack(spacing: 0) {
            if let timer = activeTimer {
                runningCard(timer: timer)
            } else if showStartForm {
                startForm
            } else {
                idleCard
            }

            if let msg = errorMessage {
                Text(msg)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .padding(.horizontal, 16)
                    .padding(.bottom, 8)
            }
        }
        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 14))
        .padding(.horizontal, 16)
        .task {
            await fetchTimerStatus()
        }
    }

    // MARK: - Idle Card

    private var idleCard: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text("Timer")
                    .font(.headline)
                Text("No active timer")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button {
                withAnimation(.spring(response: 0.3)) {
                    showStartForm = true
                }
            } label: {
                Label("Start", systemImage: "play.fill")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Color.green, in: Capsule())
            }
            .accessibilityLabel("Start timer")
        }
        .padding(16)
    }

    // MARK: - Start Form

    private var startForm: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("New Timer")
                    .font(.headline)
                Spacer()
                Button {
                    withAnimation(.spring(response: 0.3)) {
                        showStartForm = false
                        newDescription = ""
                        newClientName = ""
                        newClientEmail = ""
                        newHourlyRate = ""
                    }
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .accessibilityLabel("Cancel")
            }

            TextField("Description", text: $newDescription)
                .textFieldStyle(.roundedBorder)
                .accessibilityLabel("Timer description")

            TextField("Client name (optional)", text: $newClientName)
                .textFieldStyle(.roundedBorder)
                .textContentType(.name)

            TextField("Client email (optional)", text: $newClientEmail)
                .textFieldStyle(.roundedBorder)
                .textContentType(.emailAddress)
                .keyboardType(.emailAddress)
                .autocapitalization(.none)

            TextField("Hourly rate", text: $newHourlyRate)
                .textFieldStyle(.roundedBorder)
                .keyboardType(.decimalPad)
                .accessibilityLabel("Hourly rate")

            Button {
                Task { await startTimer() }
            } label: {
                Group {
                    if isActing {
                        ProgressView().progressViewStyle(.circular).tint(.white)
                    } else {
                        Label("Start Timer", systemImage: "play.fill")
                            .font(.subheadline.weight(.semibold))
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 40)
                .foregroundStyle(.white)
                .background(startButtonBackground, in: RoundedRectangle(cornerRadius: 8))
            }
            .disabled(isActing || newDescription.trimmingCharacters(in: .whitespaces).isEmpty)
        }
        .padding(16)
    }

    private var startButtonBackground: Color {
        newDescription.trimmingCharacters(in: .whitespaces).isEmpty || isActing
            ? Color(.systemGray3)
            : .green
    }

    // MARK: - Running Card

    private func runningCard(timer: ActiveTimerResponse) -> some View {
        VStack(spacing: 10) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(timer.description)
                        .font(.headline)
                        .lineLimit(1)
                    if let client = timer.clientName, !client.isEmpty {
                        Text(client)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                // Live elapsed clock
                TimelineView(.periodic(from: .now, by: 1)) { _ in
                    VStack(alignment: .trailing, spacing: 2) {
                        Text(elapsedString(since: timer.startedAt))
                            .font(.system(.title3, design: .monospaced).weight(.semibold))
                            .foregroundStyle(.primary)
                        Text(estimatedAmount(timer: timer))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            HStack(spacing: 12) {
                // Discard
                Button(role: .destructive) {
                    showDiscardConfirm = true
                } label: {
                    Label("Discard", systemImage: "trash")
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .frame(height: 38)
                        .background(Color(.systemFill), in: RoundedRectangle(cornerRadius: 8))
                }
                .accessibilityLabel("Discard timer")
                .confirmationDialog(
                    "Discard this timer?",
                    isPresented: $showDiscardConfirm,
                    titleVisibility: .visible
                ) {
                    Button("Discard", role: .destructive) {
                        Task { await discardTimer(id: timer.id) }
                    }
                    Button("Cancel", role: .cancel) {}
                }

                // Stop
                Button {
                    Task { await stopTimer(id: timer.id) }
                } label: {
                    Group {
                        if isActing {
                            ProgressView().progressViewStyle(.circular).tint(.white)
                        } else {
                            Label("Stop", systemImage: "stop.fill")
                                .font(.subheadline.weight(.semibold))
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 38)
                    .foregroundStyle(.white)
                    .background(Color.red, in: RoundedRectangle(cornerRadius: 8))
                }
                .disabled(isActing)
                .accessibilityLabel("Stop timer")
            }
        }
        .padding(16)
    }

    // MARK: - Helpers

    private func elapsedString(since startedAtString: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let start = formatter.date(from: startedAtString)
            ?? ISO8601DateFormatter().date(from: startedAtString)
            ?? Date()
        let elapsed = max(0, Int(Date().timeIntervalSince(start)))
        let h = elapsed / 3600
        let m = (elapsed % 3600) / 60
        let s = elapsed % 60
        return String(format: "%02d:%02d:%02d", h, m, s)
    }

    private func estimatedAmount(timer: ActiveTimerResponse) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let start = formatter.date(from: timer.startedAt)
            ?? ISO8601DateFormatter().date(from: timer.startedAt)
            ?? Date()
        let hours = Date().timeIntervalSince(start) / 3600.0
        let rate = Double(timer.hourlyRate) ?? 0
        let amount = hours * rate
        return String(format: "$%.2f", amount)
    }

    // MARK: - API Calls

    private func fetchTimerStatus() async {
        isLoadingStatus = true
        defer { isLoadingStatus = false }
        do {
            let response: ActiveTimerResponse? = try await appState.api.get("time/timer/status/")
            await MainActor.run { activeTimer = response }
        } catch {
            // Silently ignore — no active timer is a valid state
            await MainActor.run { activeTimer = nil }
        }
    }

    private func startTimer() async {
        guard !newDescription.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        isActing = true
        errorMessage = nil
        defer { isActing = false }

        struct StartBody: Encodable {
            let description: String
            let clientName: String
            let clientEmail: String
            let hourlyRate: String
        }

        do {
            let body = StartBody(
                description: newDescription.trimmingCharacters(in: .whitespaces),
                clientName: newClientName,
                clientEmail: newClientEmail,
                hourlyRate: newHourlyRate.isEmpty ? "0" : newHourlyRate
            )
            let timer: ActiveTimerResponse = try await appState.api.post("time/timer/start/", body: body)
            HapticManager.impact(.heavy)
            await MainActor.run {
                activeTimer = timer
                showStartForm = false
                newDescription = ""
                newClientName = ""
                newClientEmail = ""
                newHourlyRate = ""
            }
        } catch {
            await MainActor.run { errorMessage = "Could not start timer." }
        }
    }

    private func stopTimer(id: Int) async {
        isActing = true
        errorMessage = nil
        defer { isActing = false }
        do {
            let _: TimeEntryResponse = try await appState.api.post("time/timer/\(id)/stop/")
            HapticManager.notification(.success)
            await MainActor.run { activeTimer = nil }
            onTimerStopped?()
        } catch {
            await MainActor.run { errorMessage = "Could not stop timer." }
        }
    }

    private func discardTimer(id: Int) async {
        isActing = true
        errorMessage = nil
        defer { isActing = false }
        do {
            let _: EmptyResponse = try await appState.api.post("time/timer/\(id)/discard/")
            HapticManager.notification(.warning)
            await MainActor.run { activeTimer = nil }
        } catch {
            await MainActor.run { errorMessage = "Could not discard timer." }
        }
    }
}

#Preview {
    TimerCardView()
        .environment(AppState())
        .padding(.vertical)
}
