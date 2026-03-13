import Foundation
import FirebaseFirestore
import CoreLocation
import Combine

@MainActor
final class ChatViewModel: ObservableObject {
    @Published var messages: [DecryptedMessage] = []
    @Published var participantLocations: [String: CLLocationCoordinate2D] = [:]
    @Published var participantNames: [String: String] = [:]
    @Published var messageText = ""
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var isLocationSharingActive: Bool

    let conversation: Conversation
    private let currentUserId: String
    private let cryptoService = CryptoService.shared
    private let firestoreService = FirestoreService.shared
    private let locationService: LocationService

    private var messageListener: ListenerRegistration?
    private var locationListener: ListenerRegistration?
    private var locationCancellable: AnyCancellable?
    private var symmetricKeys: [String: SymmetricKey] = [:] // peerId -> key

    init(conversation: Conversation, currentUserId: String, locationService: LocationService) {
        self.conversation = conversation
        self.currentUserId = currentUserId
        self.locationService = locationService
        self.isLocationSharingActive = conversation.isLocationSharingActive
        self.participantNames = conversation.participantNames

        Task {
            await deriveKeys()
            startMessageListener()
            startLocationListener()
            startLocationBroadcast()
        }
    }

    deinit {
        messageListener?.remove()
        locationListener?.remove()
        locationCancellable?.cancel()
    }

    // MARK: - Key Derivation

    private func deriveKeys() async {
        guard let convId = conversation.id else { return }

        let peerIds = conversation.participants.filter { $0 != currentUserId }

        for peerId in peerIds {
            do {
                let peerUser = try await firestoreService.fetchUser(userId: peerId)
                guard let peerUser = peerUser else { continue }

                let key = try cryptoService.deriveSharedKey(
                    peerPublicKeyData: peerUser.publicKey,
                    conversationId: convId
                )
                symmetricKeys[peerId] = key
            } catch {
                print("Failed to derive key for peer \(peerId): \(error)")
            }
        }
    }

    // MARK: - Send Message

    func sendMessage() async {
        let text = messageText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, let convId = conversation.id else { return }

        // Use the first peer's key for encryption (1-to-1 chat)
        guard let key = symmetricKeys.values.first else {
            errorMessage = "No se pudo encriptar el mensaje"
            return
        }

        messageText = ""

        do {
            let encryptedContent = try cryptoService.encrypt(text, with: key)

            try await firestoreService.sendMessage(
                conversationId: convId,
                senderId: currentUserId,
                encryptedContent: encryptedContent
            )
        } catch {
            errorMessage = "Error al enviar mensaje: \(error.localizedDescription)"
            messageText = text // Restore text on failure
        }
    }

    // MARK: - Message Listener

    private func startMessageListener() {
        guard let convId = conversation.id else { return }

        messageListener = firestoreService.listenToMessages(conversationId: convId) { [weak self] messages in
            Task { @MainActor in
                self?.decryptMessages(messages)
            }
        }
    }

    private func decryptMessages(_ encryptedMessages: [Message]) {
        // For 1-to-1 chat, use the same key to decrypt all messages
        guard let key = symmetricKeys.values.first else { return }

        messages = encryptedMessages.compactMap { message in
            guard let decryptedText = try? cryptoService.decrypt(message.encryptedContent, with: key) else {
                return nil
            }

            return DecryptedMessage(
                id: message.id ?? UUID().uuidString,
                senderId: message.senderId,
                content: decryptedText,
                timestamp: message.timestamp.dateValue(),
                type: message.type,
                isFromCurrentUser: message.senderId == currentUserId
            )
        }
    }

    // MARK: - Location Listener

    private func startLocationListener() {
        guard let convId = conversation.id else { return }
        guard let key = symmetricKeys.values.first else { return }

        locationListener = firestoreService.listenToLocations(conversationId: convId) { [weak self] locations in
            Task { @MainActor in
                self?.decryptLocations(locations, key: key)
            }
        }
    }

    private func decryptLocations(_ locations: [LocationUpdate], key: SymmetricKey) {
        for location in locations {
            guard let userId = location.id else { continue }

            if let coords = try? cryptoService.decryptLocation(
                encryptedLat: location.encryptedLatitude,
                encryptedLon: location.encryptedLongitude,
                with: key
            ) {
                participantLocations[userId] = CLLocationCoordinate2D(
                    latitude: coords.latitude,
                    longitude: coords.longitude
                )
            }
        }
    }

    // MARK: - Location Broadcast

    private func startLocationBroadcast() {
        guard isLocationSharingActive else { return }

        locationService.startTracking()

        locationCancellable = locationService.$currentLocation
            .compactMap { $0 }
            .sink { [weak self] location in
                Task { @MainActor in
                    await self?.broadcastLocation(location)
                }
            }
    }

    private func broadcastLocation(_ location: CLLocation) async {
        guard let convId = conversation.id,
              let key = symmetricKeys.values.first else { return }

        do {
            let (encLat, encLon) = try cryptoService.encryptLocation(
                latitude: location.coordinate.latitude,
                longitude: location.coordinate.longitude,
                with: key
            )

            try await firestoreService.updateLocation(
                conversationId: convId,
                userId: currentUserId,
                encryptedLat: encLat,
                encryptedLon: encLon
            )
        } catch {
            print("Failed to broadcast location: \(error)")
        }
    }

    func toggleLocationSharing() async {
        guard let convId = conversation.id else { return }

        isLocationSharingActive.toggle()

        if isLocationSharingActive {
            startLocationBroadcast()
        } else {
            locationCancellable?.cancel()
            locationService.stopTracking()
        }

        try? await firestoreService.toggleLocationSharing(
            conversationId: convId,
            isActive: isLocationSharingActive
        )
    }
}
