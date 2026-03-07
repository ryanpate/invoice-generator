import Foundation

@Observable
final class AppState {
    let api: APIClient
    let auth: AuthManager
    let store: StoreManager
    let biometric: BiometricManager

    var isFaceIDEnabled: Bool {
        get { UserDefaults.standard.bool(forKey: "faceIDEnabled") }
        set { UserDefaults.standard.set(newValue, forKey: "faceIDEnabled") }
    }

    var isUnlocked: Bool = false

    init() {
        let api = APIClient()
        self.api = api
        self.auth = AuthManager(api: api)
        self.store = StoreManager(api: api)
        self.biometric = BiometricManager()
    }
}
