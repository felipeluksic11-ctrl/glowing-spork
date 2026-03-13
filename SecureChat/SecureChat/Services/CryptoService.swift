import Foundation
import CryptoKit

enum CryptoError: Error, LocalizedError {
    case keyGenerationFailed
    case keyNotFound
    case encryptionFailed
    case decryptionFailed
    case invalidPublicKey
    case keyDerivationFailed

    var errorDescription: String? {
        switch self {
        case .keyGenerationFailed: return "Failed to generate encryption keys"
        case .keyNotFound: return "Encryption key not found"
        case .encryptionFailed: return "Failed to encrypt data"
        case .decryptionFailed: return "Failed to decrypt data"
        case .invalidPublicKey: return "Invalid public key"
        case .keyDerivationFailed: return "Failed to derive shared key"
        }
    }
}

final class CryptoService {
    static let shared = CryptoService()

    private let keychainService = KeychainService.shared
    private let privateKeyIdentifier = "identity_private_key"

    // Cache derived symmetric keys per conversation
    private var symmetricKeyCache: [String: SymmetricKey] = [:]

    private init() {}

    // MARK: - Key Generation

    /// Generate a new Curve25519 key pair. Stores private key in Keychain, returns public key data.
    @discardableResult
    func generateKeyPair() throws -> Data {
        let privateKey = Curve25519.KeyAgreement.PrivateKey()
        try keychainService.save(
            privateKey.rawRepresentation,
            forKey: privateKeyIdentifier
        )
        return privateKey.publicKey.rawRepresentation
    }

    /// Check if a key pair already exists in the Keychain.
    var hasKeyPair: Bool {
        keychainService.exists(forKey: privateKeyIdentifier)
    }

    /// Get the public key data to upload to Firestore.
    func getPublicKeyData() throws -> Data {
        let privateKey = try loadPrivateKey()
        return privateKey.publicKey.rawRepresentation
    }

    // MARK: - Key Agreement

    /// Derive a symmetric key for a conversation using Diffie-Hellman key agreement.
    func deriveSharedKey(
        peerPublicKeyData: Data,
        conversationId: String
    ) throws -> SymmetricKey {
        // Check cache first
        if let cached = symmetricKeyCache[conversationId] {
            return cached
        }

        let myPrivateKey = try loadPrivateKey()

        guard let peerPublicKey = try? Curve25519.KeyAgreement.PublicKey(
            rawRepresentation: peerPublicKeyData
        ) else {
            throw CryptoError.invalidPublicKey
        }

        guard let sharedSecret = try? myPrivateKey.sharedSecretFromKeyAgreement(
            with: peerPublicKey
        ) else {
            throw CryptoError.keyDerivationFailed
        }

        // Derive a 256-bit symmetric key using HKDF
        // Salt with conversationId to make keys conversation-specific
        let symmetricKey = sharedSecret.hkdfDerivedSymmetricKey(
            using: SHA256.self,
            salt: Data(conversationId.utf8),
            sharedInfo: Data("SecureChat-v1".utf8),
            outputByteCount: 32
        )

        symmetricKeyCache[conversationId] = symmetricKey
        return symmetricKey
    }

    /// Clear cached key for a conversation.
    func clearCachedKey(for conversationId: String) {
        symmetricKeyCache.removeValue(forKey: conversationId)
    }

    // MARK: - Message Encryption

    /// Encrypt a plaintext string using AES-GCM.
    func encrypt(_ plaintext: String, with key: SymmetricKey) throws -> Data {
        guard let data = plaintext.data(using: .utf8) else {
            throw CryptoError.encryptionFailed
        }

        guard let sealedBox = try? AES.GCM.seal(data, using: key),
              let combined = sealedBox.combined else {
            throw CryptoError.encryptionFailed
        }

        return combined
    }

    /// Decrypt AES-GCM encrypted data back to a string.
    func decrypt(_ ciphertext: Data, with key: SymmetricKey) throws -> String {
        guard let sealedBox = try? AES.GCM.SealedBox(combined: ciphertext),
              let decryptedData = try? AES.GCM.open(sealedBox, using: key),
              let plaintext = String(data: decryptedData, encoding: .utf8) else {
            throw CryptoError.decryptionFailed
        }

        return plaintext
    }

    // MARK: - Location Encryption

    /// Encrypt latitude and longitude values.
    func encryptLocation(
        latitude: Double,
        longitude: Double,
        with key: SymmetricKey
    ) throws -> (encryptedLat: Data, encryptedLon: Data) {
        let latData = withUnsafeBytes(of: latitude) { Data($0) }
        let lonData = withUnsafeBytes(of: longitude) { Data($0) }

        guard let latBox = try? AES.GCM.seal(latData, using: key),
              let latCombined = latBox.combined,
              let lonBox = try? AES.GCM.seal(lonData, using: key),
              let lonCombined = lonBox.combined else {
            throw CryptoError.encryptionFailed
        }

        return (latCombined, lonCombined)
    }

    /// Decrypt encrypted latitude and longitude values.
    func decryptLocation(
        encryptedLat: Data,
        encryptedLon: Data,
        with key: SymmetricKey
    ) throws -> (latitude: Double, longitude: Double) {
        guard let latBox = try? AES.GCM.SealedBox(combined: encryptedLat),
              let latData = try? AES.GCM.open(latBox, using: key),
              let lonBox = try? AES.GCM.SealedBox(combined: encryptedLon),
              let lonData = try? AES.GCM.open(lonBox, using: key) else {
            throw CryptoError.decryptionFailed
        }

        let latitude = latData.withUnsafeBytes { $0.load(as: Double.self) }
        let longitude = lonData.withUnsafeBytes { $0.load(as: Double.self) }

        return (latitude, longitude)
    }

    // MARK: - Private Helpers

    private func loadPrivateKey() throws -> Curve25519.KeyAgreement.PrivateKey {
        let rawKey = try keychainService.load(forKey: privateKeyIdentifier)
        guard let privateKey = try? Curve25519.KeyAgreement.PrivateKey(
            rawRepresentation: rawKey
        ) else {
            throw CryptoError.keyNotFound
        }
        return privateKey
    }
}
