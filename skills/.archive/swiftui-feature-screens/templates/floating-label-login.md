# Modern LoginView + FloatingTextField (copy-ready)

Reuse this for any "make the sign-in pretty AND actually navigate after auth" task.
Two fixes baked in:
1. **No hang** — the `@main App` switches on `appState.isSignedIn` (Firebase
   `addStateDidChangeListener`), NOT a dead one-shot `@State isLoggedIn` set in `.onAppear`.
2. **Modern labels** — `FloatingTextField` uses `@FocusState`; the label animates up
   when focused/filled, with a leading icon and a secure eye toggle.

## App entry (AnglerGOApp.swift) — bind to the auth listener

```swift
@main
struct AnglerGOApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @StateObject private var appState = AppState()   // AppState.isSignedIn is @Published, driven by addStateDidChangeListener

    var body: some Scene {
        WindowGroup {
            Group {
                if appState.isSignedIn {
                    MainTabView().environmentObject(appState)
                } else {
                    LoginView()
                }
            }
        }
    }
}
```

## LoginView.swift (trimmed — keep auth actions; they need NOT flip any flag)

Key points: `FloatingTextField(title:icon:text:isSecure:...)`, gradient background,
white card, `ProgressView` spinner in the Sign In button, asset-free `GoogleGlyph`
(4-color ring drawn with SwiftUI — no image asset required so nothing breaks the build),
error text turns green for success/reset messages.

```swift
import SwiftUI
import FirebaseAuth
import GoogleSignIn
import FirebaseCore

struct LoginView: View {
    @State private var email = ""
    @State private var password = ""
    @State private var errorMessage = ""
    @State private var isLoading = false

    var body: some View {
        ZStack {
            LinearGradient(colors: [Color(red:0.05,green:0.29,blue:0.43),
                                    Color(red:0.04,green:0.45,blue:0.55),
                                    Color(red:0.06,green:0.62,blue:0.55)],
                           startPoint: .topLeading, endPoint: .bottomTrailing)
                .ignoresSafeArea()
            ScrollView {
                VStack(spacing: 22) {
                    // brand header (wave glyph + "AnglerGO")
                    formCard
                    errorText
                }
                .padding(.horizontal, 24).padding(.vertical, 40)
            }
        }
    }

    private var formCard: some View {
        VStack(spacing: 16) {
            FloatingTextField(title: "Email", icon: "envelope.fill",
                              text: $email, keyboard: .emailAddress, contentType: .emailAddress)
            FloatingTextField(title: "Password", icon: "lock.fill",
                              text: $password, isSecure: true, contentType: .password)
            // Sign In (gradient + spinner), Create account row, "or" divider, Google button
        }
        .padding(22)
        .background(RoundedRectangle(cornerRadius: 22, style: .continuous).fill(.white)
            .shadow(color: .black.opacity(0.18), radius: 20, x: 0, y: 10))
    }

    private var errorText: some View {
        Group {
            if !errorMessage.isEmpty {
                Text(errorMessage)
                    .font(.footnote)
                    .foregroundStyle(errorMessage.contains("✅") ? .green : .red)
                    .multilineTextAlignment(.center)
            }
        }
    }
    // login()/signUp()/signInWithGoogle()/forgotPassword() call Firebase only;
    // they set isLoading + errorMessage, and rely on AppState's listener to navigate.
}
```

## FloatingTextField.swift (reusable component)

```swift
struct FloatingTextField: View {
    let title: String
    let icon: String
    @Binding var text: String
    var isSecure = false
    var keyboard: UIKeyboardType = .default
    var contentType: UITextContentType? = nil

    @FocusState private var isFocused: Bool
    @State private var showPassword = false
    private var active: Bool { isFocused || !text.isEmpty }

    var body: some View {
        ZStack(alignment: .leading) {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .foregroundStyle(isFocused ? Color.blue : Color.gray).frame(width: 20)
                ZStack(alignment: .leading) {
                    Text(title)
                        .font(.system(size: active ? 11 : 16))
                        .foregroundStyle(isFocused ? Color.blue : Color(.placeholderText))
                        .offset(y: active ? -22 : 0)
                        .padding(.leading, 2)
                        .background(Color(.secondarySystemBackground))
                        .animation(.easeOut(duration: 0.18), value: active)
                    Group {
                        if isSecure {
                            showPassword ? AnyView(TextField("", text: $text).focused($isFocused))
                                         : AnyView(SecureField("", text: $text).focused($isFocused))
                        } else {
                            TextField("", text: $text).focused($isFocused)
                        }
                    }
                    .keyboardType(keyboard).textContentType(contentType)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                }
                if isSecure {
                    Button { showPassword.toggle() } label: {
                        Image(systemName: showPassword ? "eye.slash.fill" : "eye.fill").foregroundStyle(.gray)
                    }
                }
            }
            .padding(.horizontal, 14).padding(.vertical, 12)
        }
        .frame(height: 60)
        .background(RoundedRectangle(cornerRadius: 14, style: .continuous)
            .fill(Color(.secondarySystemBackground))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(isFocused ? Color.blue : Color.clear, lineWidth: 1.5)))
    }
}
```

## Pitfalls to carry over
- The `@main App` MUST NOT keep a manual `isLoggedIn` flag — it causes the exact
  "Firebase connects but screen stuck on login" symptom. One source of truth only.
- `GoogleGlyph`: draw the 4-color ring with 4 trimmed `Circle().stroke` + `rotationEffect`,
  never reference a Google asset that isn't in the bundle.
- After auth actions, do NOT call any navigation yourself; the listener does it.
- Keep `isLoading`/`errorMessage` UI-state only.
