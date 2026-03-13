import SwiftUI

struct ChatView: View {
    @StateObject private var viewModel: ChatViewModel
    @State private var showFullScreenMap = false
    @FocusState private var isInputFocused: Bool

    private let otherUserName: String

    init(conversation: Conversation, currentUserId: String, locationService: LocationService) {
        _viewModel = StateObject(wrappedValue: ChatViewModel(
            conversation: conversation,
            currentUserId: currentUserId,
            locationService: locationService
        ))

        // Get other participant name
        let otherName = conversation.participantNames.first { $0.key != currentUserId }?.value
        self.otherUserName = otherName ?? "Chat"
    }

    var body: some View {
        VStack(spacing: 0) {
            // Mini map
            if viewModel.isLocationSharingActive && !viewModel.participantLocations.isEmpty {
                ChatMapView(
                    locations: viewModel.participantLocations,
                    participantNames: viewModel.participantNames
                )
                .frame(height: 150)
                .onTapGesture { showFullScreenMap = true }

                Divider()
            }

            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(viewModel.messages) { message in
                            MessageBubbleView(message: message)
                                .id(message.id)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                }
                .onChange(of: viewModel.messages.count) {
                    if let lastId = viewModel.messages.last?.id {
                        withAnimation(.easeOut(duration: 0.2)) {
                            proxy.scrollTo(lastId, anchor: .bottom)
                        }
                    }
                }
            }

            Divider()

            // Input bar
            HStack(spacing: 12) {
                // Location toggle
                Button {
                    Task { await viewModel.toggleLocationSharing() }
                } label: {
                    Image(systemName: viewModel.isLocationSharingActive
                          ? "location.fill" : "location.slash")
                    .foregroundStyle(viewModel.isLocationSharingActive ? .green : .gray)
                }

                TextField("Mensaje encriptado...", text: $viewModel.messageText, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(1...4)
                    .focused($isInputFocused)

                Button {
                    Task { await viewModel.sendMessage() }
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.title2)
                        .foregroundStyle(.blue)
                }
                .disabled(viewModel.messageText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
        }
        .navigationTitle(otherUserName)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showFullScreenMap = true
                } label: {
                    Image(systemName: "map")
                }
            }
        }
        .fullScreenCover(isPresented: $showFullScreenMap) {
            FullScreenMapView(
                locations: viewModel.participantLocations,
                participantNames: viewModel.participantNames
            )
        }
        .alert("Error", isPresented: .init(
            get: { viewModel.errorMessage != nil },
            set: { if !$0 { viewModel.errorMessage = nil } }
        )) {
            Button("OK") { viewModel.errorMessage = nil }
        } message: {
            Text(viewModel.errorMessage ?? "")
        }
    }
}
