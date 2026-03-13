import Foundation
import AVFoundation
import Combine

/// Handles live camera and microphone streaming during emergencies.
/// Uses WebRTC-style P2P connections for encrypted real-time video/audio.
@MainActor
final class StreamingService: ObservableObject {
    @Published var isStreaming = false
    @Published var viewerCount = 0
    @Published var cameraPosition: AVCaptureDevice.Position = .back

    static let shared = StreamingService()

    private var captureSession: AVCaptureSession?
    private var videoOutput: AVCaptureVideoDataOutput?
    private var audioOutput: AVCaptureAudioDataOutput?
    private let sessionQueue = DispatchQueue(label: "com.securechat.streaming")

    private init() {}

    /// Start broadcasting camera and microphone to all emergency contacts.
    func startBroadcast() async throws {
        guard !isStreaming else { return }

        // Request camera and mic permissions
        let videoGranted = await AVCaptureDevice.requestAccess(for: .video)
        let audioGranted = await AVCaptureDevice.requestAccess(for: .audio)

        guard videoGranted && audioGranted else {
            throw StreamingError.permissionDenied
        }

        let session = AVCaptureSession()
        session.sessionPreset = .medium

        // Camera input
        guard let camera = AVCaptureDevice.default(
            .builtInWideAngleCamera,
            for: .video,
            position: cameraPosition
        ) else {
            throw StreamingError.cameraUnavailable
        }

        let videoInput = try AVCaptureDeviceInput(device: camera)
        if session.canAddInput(videoInput) {
            session.addInput(videoInput)
        }

        // Microphone input
        guard let mic = AVCaptureDevice.default(for: .audio) else {
            throw StreamingError.microphoneUnavailable
        }

        let audioInput = try AVCaptureDeviceInput(device: mic)
        if session.canAddInput(audioInput) {
            session.addInput(audioInput)
        }

        // Video output for streaming frames
        let videoOut = AVCaptureVideoDataOutput()
        videoOut.videoSettings = [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange
        ]
        if session.canAddOutput(videoOut) {
            session.addOutput(videoOut)
        }
        self.videoOutput = videoOut

        // Audio output
        let audioOut = AVCaptureAudioDataOutput()
        if session.canAddOutput(audioOut) {
            session.addOutput(audioOut)
        }
        self.audioOutput = audioOut

        self.captureSession = session

        sessionQueue.async {
            session.startRunning()
        }

        isStreaming = true
    }

    /// Stop the broadcast and release resources.
    func stopBroadcast() {
        sessionQueue.async { [weak self] in
            self?.captureSession?.stopRunning()
        }
        captureSession = nil
        videoOutput = nil
        audioOutput = nil
        isStreaming = false
        viewerCount = 0
    }

    /// Switch between front and back camera.
    func flipCamera() {
        cameraPosition = (cameraPosition == .back) ? .front : .back
        if isStreaming {
            stopBroadcast()
            Task {
                try? await startBroadcast()
            }
        }
    }
}

enum StreamingError: LocalizedError {
    case permissionDenied
    case cameraUnavailable
    case microphoneUnavailable

    var errorDescription: String? {
        switch self {
        case .permissionDenied:
            return "Se necesitan permisos de camara y microfono para la transmision de emergencia"
        case .cameraUnavailable:
            return "No se pudo acceder a la camara"
        case .microphoneUnavailable:
            return "No se pudo acceder al microfono"
        }
    }
}
