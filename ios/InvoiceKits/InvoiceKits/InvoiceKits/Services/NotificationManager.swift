import UserNotifications
import UIKit

@Observable
final class NotificationManager: NSObject, UNUserNotificationCenterDelegate {
    var isPermissionGranted = false
    var deviceToken: String?

    private let api: APIClient

    init(api: APIClient) {
        self.api = api
        super.init()
        UNUserNotificationCenter.current().delegate = self
    }

    func requestPermission() async {
        do {
            let granted = try await UNUserNotificationCenter.current().requestAuthorization(
                options: [.alert, .badge, .sound]
            )
            await MainActor.run { isPermissionGranted = granted }
            if granted {
                await registerForRemoteNotifications()
            }
        } catch {
            print("Notification permission error: \(error)")
        }
    }

    @MainActor
    private func registerForRemoteNotifications() {
        UIApplication.shared.registerForRemoteNotifications()
    }

    func handleDeviceToken(_ tokenData: Data) {
        let token = tokenData.map { String(format: "%02.2hhx", $0) }.joined()
        deviceToken = token
        Task {
            await sendTokenToBackend(token)
        }
    }

    private func sendTokenToBackend(_ token: String) async {
        struct Body: Encodable {
            let token: String
            let platform: String
        }
        let _: EmptyResponse? = try? await api.post(
            "devices/register/",
            body: Body(token: token, platform: "ios")
        )
    }

    // MARK: - UNUserNotificationCenterDelegate

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        [.banner, .badge, .sound]
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        let userInfo = response.notification.request.content.userInfo
        if let invoiceId = userInfo["invoice_id"] as? Int {
            await MainActor.run {
                NotificationCenter.default.post(
                    name: .navigateToInvoice,
                    object: nil,
                    userInfo: ["invoiceId": invoiceId]
                )
            }
        }
    }
}

extension Notification.Name {
    static let navigateToInvoice = Notification.Name("navigateToInvoice")
}
