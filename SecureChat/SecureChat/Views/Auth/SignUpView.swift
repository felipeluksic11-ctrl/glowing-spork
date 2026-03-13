import SwiftUI

struct SignUpView: View {
    @StateObject private var viewModel: AuthViewModel
    @Environment(\.dismiss) private var dismiss

    init(authService: AuthService) {
        _viewModel = StateObject(wrappedValue: AuthViewModel(authService: authService))
    }

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            VStack(spacing: 8) {
                Image(systemName: "person.badge.key.fill")
                    .font(.system(size: 50))
                    .foregroundStyle(.blue)

                Text("Crear Cuenta")
                    .font(.title.bold())

                Text("Se generaran tus llaves de encriptacion")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            VStack(spacing: 16) {
                TextField("Nombre completo", text: $viewModel.displayName)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.name)

                TextField("Nombre de usuario", text: $viewModel.username)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.username)
                    .autocapitalization(.none)

                TextField("Email", text: $viewModel.email)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.emailAddress)
                    .autocapitalization(.none)
                    .keyboardType(.emailAddress)

                SecureField("Contrasena (min 6 caracteres)", text: $viewModel.password)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.newPassword)
            }

            if let error = viewModel.errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
            }

            Button {
                Task {
                    await viewModel.signUp()
                    if viewModel.errorMessage == nil {
                        dismiss()
                    }
                }
            } label: {
                if viewModel.isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                } else {
                    Text("Registrarse")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(viewModel.isLoading)

            Spacer()
        }
        .padding(.horizontal, 32)
        .navigationBarTitleDisplayMode(.inline)
    }
}
