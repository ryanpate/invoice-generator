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
        let auth = AuthManager(api: api)
        self.api = api
        self.auth = auth
        self.store = StoreManager(api: api, auth: auth)
        self.biometric = BiometricManager()
    }
}
