import Foundation
import FirebaseAuth
import FirebaseFirestore

@MainActor
final class AuthService: ObservableObject {
    @Published var currentUser: FirebaseAuth.User?
    @Published var isAuthenticated = false
    @Published var isLoading = false
    @Published var errorMessage: String?

    private var authListener: AuthStateDidChangeListenerHandle?
    private let db = Firestore.firestore()
    private let cryptoService = CryptoService.shared

    init() {
        authListener = Auth.auth().addStateDidChangeListener { [weak self] _, user in
            self?.currentUser = user
            self?.isAuthenticated = user != nil
        }
    }

    deinit {
        if let listener = authListener {
            Auth.auth().removeStateDidChangeListener(listener)
        }
    }

    // MARK: - Sign Up

    func signUp(email: String, password: String, displayName: String, username: String) async throws {
        isLoading = true
        errorMessage = nil

        defer { isLoading = false }

        // Create Firebase Auth user
        let result = try await Auth.auth().createUser(withEmail: email, password: password)
        let userId = result.user.uid

        // Generate E2E encryption key pair
        let publicKeyData = try cryptoService.generateKeyPair()

        // Create user profile in Firestore
        let userData: [String: Any] = [
            "displayName": displayName,
            "username": username.lowercased(),
            "publicKey": publicKeyData,
            "createdAt": Timestamp()
        ]

        try await db.collection("users").document(userId).setData(userData)
    }

    // MARK: - Sign In

    func signIn(email: String, password: String) async throws {
        isLoading = true
        errorMessage = nil

        defer { isLoading = false }

        try await Auth.auth().signIn(withEmail: email, password: password)

        // Ensure key pair exists locally (in case of new device)
        if !cryptoService.hasKeyPair {
            // Generate new keys and update Firestore
            let publicKeyData = try cryptoService.generateKeyPair()
            guard let userId = Auth.auth().currentUser?.uid else { return }

            try await db.collection("users").document(userId).updateData([
                "publicKey": publicKeyData
            ])
        }
    }

    // MARK: - Sign Out

    func signOut() throws {
        try Auth.auth().signOut()
    }

    // MARK: - Current User ID

    var currentUserId: String? {
        Auth.auth().currentUser?.uid
    }
}
