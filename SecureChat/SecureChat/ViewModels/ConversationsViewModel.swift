import Foundation
import FirebaseFirestore

@MainActor
final class ConversationsViewModel: ObservableObject {
    @Published var conversations: [Conversation] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let firestoreService = FirestoreService.shared
    private let cryptoService = CryptoService.shared
    private let currentUserId: String
    private var listener: ListenerRegistration?

    init(currentUserId: String) {
        self.currentUserId = currentUserId
        startListening()
    }

    deinit {
        listener?.remove()
    }

    func startListening() {
        listener?.remove()
        isLoading = true

        listener = firestoreService.listenToConversations(userId: currentUserId) { [weak self] conversations in
            Task { @MainActor in
                self?.conversations = conversations
                self?.isLoading = false
            }
        }
    }

    func createConversation(with contact: AppUser) async -> String? {
        guard let contactId = contact.id else { return nil }

        do {
            // Check if conversation already exists
            if let existing = try await firestoreService.findExistingConversation(
                between: currentUserId,
                and: contactId
            ) {
                return existing.id
            }

            // Fetch current user's display name
            let currentUser = try await firestoreService.fetchUser(userId: currentUserId)
            let myName = currentUser?.displayName ?? "Usuario"

            let participants = [currentUserId, contactId]
            let names = [
                currentUserId: myName,
                contactId: contact.displayName
            ]

            let conversationId = try await firestoreService.createConversation(
                participants: participants,
                participantNames: names
            )

            return conversationId
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func otherParticipantName(in conversation: Conversation) -> String {
        for (userId, name) in conversation.participantNames {
            if userId != currentUserId {
                return name
            }
        }
        return "Chat"
    }

    func formattedTimestamp(_ timestamp: Timestamp?) -> String {
        guard let timestamp = timestamp else { return "" }
        let date = timestamp.dateValue()
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        formatter.locale = Locale(identifier: "es")
        return formatter.localizedString(for: date, relativeTo: Date())
    }
}
