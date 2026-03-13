import Foundation
import UserNotifications
import FirebaseMessaging

@MainActor
final class NotificationService: NSObject, ObservableObject {
    @Published var fcmToken: String?

    static let shared = NotificationService()

    private override init() {
        super.init()
    }

    func requestPermission() async -> Bool {
        do {
            let granted = try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .badge, .sound])
            return granted
        } catch {
            print("Notification permission error: \(error)")
            return false
        }
    }

    func setupFCM() {
        Messaging.messaging().delegate = self
    }
}

// MARK: - MessagingDelegate

extension NotificationService: MessagingDelegate {
    nonisolated func messaging(
        _ messaging: Messaging,
        didReceiveRegistrationToken fcmToken: String?
    ) {
        guard let token = fcmToken else { return }

        Task { @MainActor in
            self.fcmToken = token

            // Update token in Firestore if user is logged in
            if let userId = FirebaseAuth.Auth.auth().currentUser?.uid {
                try? await FirestoreService.shared.updateFCMToken(token, for: userId)
            }
        }
    }
}

// MARK: - UNUserNotificationCenterDelegate

extension NotificationService: UNUserNotificationCenterDelegate {
    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        // Show notification banner even when app is in foreground
        completionHandler([.banner, .sound, .badge])
    }

    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        // Handle notification tap - navigate to conversation
        let userInfo = response.notification.request.content.userInfo
        if let conversationId = userInfo["conversationId"] as? String {
            NotificationCenter.default.post(
                name: .openConversation,
                object: nil,
                userInfo: ["conversationId": conversationId]
            )
        }
        completionHandler()
    }
}

extension Notification.Name {
    static let openConversation = Notification.Name("openConversation")
}
