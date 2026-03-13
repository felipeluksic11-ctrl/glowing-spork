import SwiftUI

struct ProfileSettingsView: View {
    @StateObject private var viewModel: ProfileViewModel
    @State private var editingName = false
    @State private var newName = ""
    private let onSignOut: () -> Void

    init(currentUserId: String, onSignOut: @escaping () -> Void) {
        _viewModel = StateObject(wrappedValue: ProfileViewModel(currentUserId: currentUserId))
        self.onSignOut = onSignOut
    }

    var body: some View {
        List {
            // Profile section
            Section {
                HStack(spacing: 16) {
                    ZStack {
                        Circle()
                            .fill(.blue.opacity(0.15))
                            .frame(width: 70, height: 70)

                        Text(String((viewModel.user?.displayName ?? "U").prefix(1)).uppercased())
                            .font(.title.bold())
                            .foregroundStyle(.blue)
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        if editingName {
                            TextField("Nombre", text: $newName)
                                .textFieldStyle(.roundedBorder)
                                .onSubmit {
                                    Task {
                                        await viewModel.updateDisplayName(newName)
                                        editingName = false
                                    }
                                }
                        } else {
                            Text(viewModel.user?.displayName ?? "...")
                                .font(.title3.weight(.semibold))
                        }

                        Text("@\(viewModel.user?.username ?? "...")")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    if !editingName {
                        Button {
                            newName = viewModel.user?.displayName ?? ""
                            editingName = true
                        } label: {
                            Image(systemName: "pencil")
                        }
                    }
                }
                .padding(.vertical, 4)
            }

            // Security section
            Section("Seguridad") {
                VStack(alignment: .leading, spacing: 8) {
                    Label("Encriptacion E2E activa", systemImage: "lock.shield.fill")
                        .foregroundStyle(.green)

                    Text("Tus mensajes y ubicacion estan protegidos con encriptacion de extremo a extremo usando Curve25519 + AES-GCM.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("Huella de llave publica")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Text(viewModel.publicKeyFingerprint)
                        .font(.system(.caption2, design: .monospaced))
                        .foregroundStyle(.primary)
                }
            }

            // Account section
            Section("Cuenta") {
                if let email = viewModel.user?.phoneNumber {
                    Label(email, systemImage: "envelope")
                }

                Button(role: .destructive) {
                    onSignOut()
                } label: {
                    Label("Cerrar sesion", systemImage: "rectangle.portrait.and.arrow.right")
                }
            }

            // App info
            Section("Informacion") {
                Label("Version 1.0.0", systemImage: "info.circle")
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Perfil")
        .task {
            await viewModel.loadProfile()
        }
    }
}
