import SwiftUI
import WebKit

/// A lean SwiftUI wrapper that loads an HTML file from the app bundle.
/// Use this to display HTML prototypes inside an iOS app without a full Safari view.
struct PrototypeWebView: UIViewRepresentable {
    let url: URL
    
    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        // Required for loading local resources (images, CSS) from the HTML file
        config.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")
        return WKWebView(frame: .zero, configuration: config)
    }
    
    func updateUIView(_ uiView: WKWebView, context: Context) {
        uiView.navigationDelegate = context.coordinator
        uiView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
    }
    
    func makeCoordinator() -> Coordinator { Coordinator() }
    
    class Coordinator: NSObject, WKNavigationDelegate {
        // Handle navigation failures and console logs for debugging
        func webView(_ webView: WKWebView, didFail navigation: WKNavigation, withError error: Error) {
            print("Navigation failed: \(error.localizedDescription)")
        }
    }
}