import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authService: AuthService
    @EnvironmentObject var locationService: LocationService

    var body: some View {
        Group {
            if authService.isAuthenticated {
                MainTabView()
            } else {
                LoginView(authService: authService)
            }
        }
        .animation(.easeInOut, value: authService.isAuthenticated)
    }
}

// MARK: - Main Tab View

struct MainTabView: View {
    @EnvironmentObject var authService: AuthService
    @EnvironmentObject var locationService: LocationService
    @State private var selectedTab = 0
    @State private var selectedConversation: Conversation?
    @State private var navigationPath = NavigationPath()

    private var currentUserId: String {
        authService.currentUserId ?? ""
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            // Chats Tab
            NavigationStack(path: $navigationPath) {
                ConversationsListView(
                    currentUserId: currentUserId,
                    selectedConversation: $selectedConversation
                )
                .navigationDestination(item: $selectedConversation) { conversation in
                    ChatView(
                        conversation: conversation,
                        currentUserId: currentUserId,
                        locationService: locationService
                    )
                }
            }
            .tabItem {
                Label("Chats", systemImage: "bubble.left.and.bubble.right.fill")
            }
            .tag(0)

            // Contacts Tab
            NavigationStack {
                ContactsListView(currentUserId: currentUserId) { contact in
                    Task {
                        let vm = ConversationsViewModel(currentUserId: currentUserId)
                        if let convId = await vm.createConversation(with: contact) {
                            // Switch to chats tab and navigate to the conversation
                            let conversation = Conversation(
                                id: convId,
                                participants: [currentUserId, contact.id ?? ""],
                                participantNames: [
                                    currentUserId: "Yo",
                                    contact.id ?? "": contact.displayName
                                ],
                                createdAt: .init(date: Date()),
                                isLocationSharingActive: true
                            )
                            selectedConversation = conversation
                            selectedTab = 0
                        }
                    }
                }
            }
            .tabItem {
                Label("Contactos", systemImage: "person.2.fill")
            }
            .tag(1)

            // Profile Tab
            NavigationStack {
                ProfileSettingsView(currentUserId: currentUserId) {
                    try? authService.signOut()
                }
            }
            .tabItem {
                Label("Perfil", systemImage: "person.circle.fill")
            }
            .tag(2)
        }
        .onAppear {
            locationService.requestPermission()
        }
    }
}
