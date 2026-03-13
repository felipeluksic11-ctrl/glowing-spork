import Foundation
import FirebaseFirestore

@MainActor
final class ProfileViewModel: ObservableObject {
    @Published var user: AppUser?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let firestoreService = FirestoreService.shared
    private let currentUserId: String

    init(currentUserId: String) {
        self.currentUserId = currentUserId
    }

    func loadProfile() async {
        isLoading = true
        do {
            user = try await firestoreService.fetchUser(userId: currentUserId)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func updateDisplayName(_ name: String) async {
        guard !name.trimmingCharacters(in: .whitespaces).isEmpty else { return }

        let db = Firestore.firestore()
        do {
            try await db.collection("users").document(currentUserId).updateData([
                "displayName": name
            ])
            user?.displayName = name
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// Returns the public key fingerprint for verification.
    var publicKeyFingerprint: String {
        guard let keyData = user?.publicKey else { return "N/A" }
        return keyData.map { String(format: "%02X", $0) }
            .chunked(into: 2)
            .map { $0.joined() }
            .joined(separator: " ")
    }
}

// MARK: - Array Chunking Helper

private extension Array {
    func chunked(into size: Int) -> [[Element]] {
        stride(from: 0, to: count, by: size).map {
            Array(self[$0..<Swift.min($0 + size, count)])
        }
    }
}
