import Foundation
import FirebaseFirestore
import CoreLocation
import AVFoundation
import UserNotifications

@MainActor
final class EmergencyService: ObservableObject {
    @Published var isEmergencyActive = false
    @Published var alertStartTime: Date?

    static let shared = EmergencyService()

    private let db = Firestore.firestore()
    private let locationService = LocationService()
    private let streamingService = StreamingService.shared
    private var audioPlayer: AVAudioPlayer?

    private init() {}

    /// Trigger emergency alert: sends push notification with alarm to all contacts,
    /// shares live location, and plays local alarm sound.
    func triggerEmergency(
        senderId: String,
        senderName: String,
        contacts: [AppUser],
        currentLocation: CLLocation?
    ) async throws {
        isEmergencyActive = true
        alertStartTime = Date()

        // 1. Create emergency document in Firestore
        let emergencyData: [String: Any] = [
            "senderId": senderId,
            "senderName": senderName,
            "timestamp": Timestamp(),
            "latitude": currentLocation?.coordinate.latitude ?? 0,
            "longitude": currentLocation?.coordinate.longitude ?? 0,
            "isActive": true,
            "contactIds": contacts.compactMap { $0.id }
        ]

        let docRef = try await db.collection("emergencies").addDocument(data: emergencyData)

        // 2. Send high-priority push notification to all contacts via their FCM tokens
        for contact in contacts {
            guard let contactId = contact.id else { continue }

            let notificationData: [String: Any] = [
                "recipientId": contactId,
                "senderId": senderId,
                "senderName": senderName,
                "type": "emergency",
                "emergencyId": docRef.documentID,
                "latitude": currentLocation?.coordinate.latitude ?? 0,
                "longitude": currentLocation?.coordinate.longitude ?? 0,
                "timestamp": Timestamp()
            ]

            try await db.collection("emergency_notifications").addDocument(data: notificationData)
        }

        // 3. Start live camera + microphone broadcast
        try await streamingService.startBroadcast()

        // 4. Play local alarm sound
        playAlarmSound()

        // 5. Start continuous location sharing at maximum frequency
        locationService.requestPermission()
        locationService.enableBackgroundUpdates()
        locationService.startTracking()
    }

    /// Stop the emergency alert.
    func stopEmergency(senderId: String) async throws {
        isEmergencyActive = false
        alertStartTime = nil

        // Update all active emergencies from this user
        let snapshot = try await db.collection("emergencies")
            .whereField("senderId", isEqualTo: senderId)
            .whereField("isActive", isEqualTo: true)
            .getDocuments()

        for doc in snapshot.documents {
            try await doc.reference.updateData([
                "isActive": false,
                "endTimestamp": Timestamp()
            ])
        }

        // Stop live broadcast
        streamingService.stopBroadcast()

        // Stop alarm sound
        stopAlarmSound()

        // Stop high-frequency location
        locationService.disableBackgroundUpdates()
        locationService.stopTracking()
    }

    /// Handle receiving an emergency alert from another user.
    func handleIncomingEmergency(
        senderName: String,
        latitude: Double,
        longitude: Double
    ) {
        // Play alarm on receiving device
        playAlarmSound()

        // Schedule a critical notification that bypasses silent mode
        let content = UNMutableNotificationContent()
        content.title = "EMERGENCIA"
        content.body = "\(senderName) ha enviado una alerta de emergencia. Toca para ver su ubicacion."
        content.sound = .defaultCritical
        content.interruptionLevel = .critical
        content.categoryIdentifier = "EMERGENCY"

        let request = UNNotificationRequest(
            identifier: "emergency-\(UUID().uuidString)",
            content: content,
            trigger: nil
        )

        UNUserNotificationCenter.current().add(request)
    }

    // MARK: - Alarm Sound

    private func playAlarmSound() {
        // Generate a siren-like tone using AVAudioPlayer
        // In production, use a bundled .caf or .wav alarm file
        AudioServicesPlayAlertSound(SystemSoundID(1005)) // System alarm sound
    }

    private func stopAlarmSound() {
        audioPlayer?.stop()
        audioPlayer = nil
    }
}
