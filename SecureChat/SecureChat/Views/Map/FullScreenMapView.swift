import SwiftUI
import MapKit

struct FullScreenMapView: View {
    @Environment(\.dismiss) private var dismiss

    let locations: [String: CLLocationCoordinate2D]
    let participantNames: [String: String]

    @State private var cameraPosition: MapCameraPosition = .automatic

    var body: some View {
        NavigationStack {
            ZStack {
                Map(position: $cameraPosition) {
                    ForEach(Array(locations.keys), id: \.self) { userId in
                        if let coord = locations[userId] {
                            Annotation(
                                participantNames[userId] ?? "Usuario",
                                coordinate: coord
                            ) {
                                VStack(spacing: 4) {
                                    ZStack {
                                        Circle()
                                            .fill(.blue)
                                            .frame(width: 40, height: 40)

                                        Text(String((participantNames[userId] ?? "U").prefix(1)).uppercased())
                                            .font(.headline.bold())
                                            .foregroundStyle(.white)
                                    }
                                    .shadow(radius: 3)

                                    Text(participantNames[userId] ?? "Usuario")
                                        .font(.caption.bold())
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 4)
                                        .background(.ultraThinMaterial)
                                        .clipShape(Capsule())
                                }
                            }
                        }
                    }
                }
                .mapStyle(.standard(elevation: .realistic))
                .mapControls {
                    MapCompass()
                    MapUserLocationButton()
                    MapScaleView()
                }

                // Participant count overlay
                VStack {
                    Spacer()

                    HStack {
                        Image(systemName: "person.2.fill")
                        Text("\(locations.count) participantes visibles")
                    }
                    .font(.caption.weight(.medium))
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(.ultraThinMaterial)
                    .clipShape(Capsule())
                    .padding(.bottom, 20)
                }
            }
            .navigationTitle("Ubicaciones")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cerrar") { dismiss() }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        withAnimation {
                            cameraPosition = .automatic
                        }
                    } label: {
                        Image(systemName: "arrow.triangle.2.circlepath")
                    }
                }
            }
        }
    }
}
