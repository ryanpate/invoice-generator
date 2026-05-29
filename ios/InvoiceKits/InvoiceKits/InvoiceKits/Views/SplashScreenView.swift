import SwiftUI

struct SplashScreenView: View {
    @State private var opacity: Double = 0

    let onFinished: () -> Void

    var body: some View {
        ZStack {
            Color.white
                .ignoresSafeArea()

            Image("SplashImage")
                .resizable()
                .scaledToFit()
                .frame(width: 220, height: 220)
        }
        .opacity(opacity)
        .onAppear {
            // Fade in
            withAnimation(.easeIn(duration: 0.6)) {
                opacity = 1.0
            }
            // Hold, then fade out
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.4) {
                withAnimation(.easeOut(duration: 0.5)) {
                    opacity = 0
                }
            }
            // Dismiss after fade out completes
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                onFinished()
            }
        }
    }
}
