import Foundation
import FirebaseFirestore
import FirebaseAuth

final class FirestoreService {
    static let shared = FirestoreService()

    private let db = Firestore.firestore()

    private init() {}

    // MARK: - Users

    func fetchUser(userId: String) async throws -> AppUser? {
        let doc = try await db.collection("users").document(userId).getDocument()
        return try? doc.data(as: AppUser.self)
    }

    func searchUsers(byUsername username: String) async throws -> [AppUser] {
        let lowercased = username.lowercased()
        let snapshot = try await db.collection("users")
            .whereField("username", isGreaterThanOrEqualTo: lowercased)
            .whereField("username", isLessThanOrEqualTo: lowercased + "\u{f8ff}")
            .limit(to: 20)
            .getDocuments()

        return snapshot.documents.compactMap { try? $0.data(as: AppUser.self) }
    }

    func updateFCMToken(_ token: String, for userId: String) async throws {
        try await db.collection("users").document(userId).updateData([
            "fcmToken": token
        ])
    }

    // MARK: - Contacts

    func addContact(userId: String, contactId: String) async throws {
        let data: [String: Any] = [
            "addedAt": Timestamp()
        ]
        try await db.collection("contacts").document(userId)
            .collection("userContacts").document(contactId).setData(data)
    }

    func fetchContacts(userId: String) async throws -> [AppUser] {
        let snapshot = try await db.collection("contacts").document(userId)
            .collection("userContacts").getDocuments()

        let contactIds = snapshot.documents.map { $0.documentID }

        var contacts: [AppUser] = []
        for contactId in contactIds {
            if let user = try await fetchUser(userId: contactId) {
                contacts.append(user)
            }
        }

        return contacts
    }

    func removeContact(userId: String, contactId: String) async throws {
        try await db.collection("contacts").document(userId)
            .collection("userContacts").document(contactId).delete()
    }

    // MARK: - Conversations

    func createConversation(participants: [String], participantNames: [String: String]) async throws -> String {
        let data: [String: Any] = [
            "participants": participants,
            "participantNames": participantNames,
            "createdAt": Timestamp(),
            "isLocationSharingActive": true
        ]

        let docRef = try await db.collection("conversations").addDocument(data: data)
        return docRef.documentID
    }

    func findExistingConversation(between userId1: String, and userId2: String) async throws -> Conversation? {
        let snapshot = try await db.collection("conversations")
            .whereField("participants", arrayContains: userId1)
            .getDocuments()

        return snapshot.documents
            .compactMap { try? $0.data(as: Conversation.self) }
            .first { $0.participants.contains(userId2) && $0.participants.count == 2 }
    }

    func listenToConversations(
        userId: String,
        onChange: @escaping ([Conversation]) -> Void
    ) -> ListenerRegistration {
        return db.collection("conversations")
            .whereField("participants", arrayContains: userId)
            .order(by: "lastMessageTimestamp", descending: true)
            .addSnapshotListener { snapshot, error in
                guard let documents = snapshot?.documents else { return }
                let conversations = documents.compactMap {
                    try? $0.data(as: Conversation.self)
                }
                onChange(conversations)
            }
    }

    // MARK: - Messages

    func sendMessage(
        conversationId: String,
        senderId: String,
        encryptedContent: Data,
        type: Message.MessageType = .text
    ) async throws {
        let messageData: [String: Any] = [
            "senderId": senderId,
            "encryptedContent": encryptedContent,
            "timestamp": Timestamp(),
            "type": type.rawValue
        ]

        // Write message
        try await db.collection("conversations").document(conversationId)
            .collection("messages").addDocument(data: messageData)

        // Update conversation's last message timestamp
        try await db.collection("conversations").document(conversationId).updateData([
            "lastMessageTimestamp": Timestamp()
        ])
    }

    func listenToMessages(
        conversationId: String,
        limit: Int = 50,
        onChange: @escaping ([Message]) -> Void
    ) -> ListenerRegistration {
        return db.collection("conversations").document(conversationId)
            .collection("messages")
            .order(by: "timestamp", descending: false)
            .limit(toLast: limit)
            .addSnapshotListener { snapshot, error in
                guard let documents = snapshot?.documents else { return }
                let messages = documents.compactMap {
                    try? $0.data(as: Message.self)
                }
                onChange(messages)
            }
    }

    // MARK: - Location

    func updateLocation(
        conversationId: String,
        userId: String,
        encryptedLat: Data,
        encryptedLon: Data
    ) async throws {
        let data: [String: Any] = [
            "encryptedLatitude": encryptedLat,
            "encryptedLongitude": encryptedLon,
            "timestamp": Timestamp()
        ]

        try await db.collection("conversations").document(conversationId)
            .collection("locations").document(userId).setData(data)
    }

    func listenToLocations(
        conversationId: String,
        onChange: @escaping ([LocationUpdate]) -> Void
    ) -> ListenerRegistration {
        return db.collection("conversations").document(conversationId)
            .collection("locations")
            .addSnapshotListener { snapshot, error in
                guard let documents = snapshot?.documents else { return }
                let locations = documents.compactMap {
                    try? $0.data(as: LocationUpdate.self)
                }
                onChange(locations)
            }
    }

    func toggleLocationSharing(conversationId: String, isActive: Bool) async throws {
        try await db.collection("conversations").document(conversationId).updateData([
            "isLocationSharingActive": isActive
        ])
    }
}
