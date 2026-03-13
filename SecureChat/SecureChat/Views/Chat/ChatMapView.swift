import SwiftUI
import MapKit

struct ChatMapView: View {
    let locations: [String: CLLocationCoordinate2D]
    let participantNames: [String: String]

    var body: some View {
        Map {
            ForEach(Array(locations.keys), id: \.self) { userId in
                if let coord = locations[userId] {
                    Annotation(
                        participantNames[userId] ?? "Usuario",
                        coordinate: coord
                    ) {
                        VStack(spacing: 2) {
                            Image(systemName: "person.circle.fill")
                                .font(.title2)
                                .foregroundStyle(.blue)
                                .background(
                                    Circle()
                                        .fill(.white)
                                        .frame(width: 28, height: 28)
                                )

                            Text(participantNames[userId] ?? "")
                                .font(.caption2.bold())
                                .foregroundStyle(.primary)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(.ultraThinMaterial)
                                .clipShape(Capsule())
                        }
                    }
                }
            }
        }
        .mapStyle(.standard(elevation: .flat))
        .mapControls {
            MapCompass()
        }
        .clipShape(RoundedRectangle(cornerRadius: 0))
    }
}
