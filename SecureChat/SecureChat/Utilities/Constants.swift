import Foundation

enum AppConstants {
    enum Firestore {
        static let usersCollection = "users"
        static let contactsCollection = "contacts"
        static let conversationsCollection = "conversations"
        static let messagesSubcollection = "messages"
        static let locationsSubcollection = "locations"
    }

    enum Location {
        static let updateIntervalSeconds: TimeInterval = 5.0
        static let distanceFilterMeters: Double = 10.0
    }

    enum Crypto {
        static let privateKeyIdentifier = "identity_private_key"
        static let appIdentifier = "SecureChat-v1"
        static let keyOutputBytes = 32
    }
}
