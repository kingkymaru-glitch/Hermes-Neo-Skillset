# Supabase iOS OAuth — Apple + Google (supabase-swift v2.53.0)

Verified recipe for wiring Apple + Google Sign-In to Supabase in a SwiftUI
iOS app. The CODE below is correct against the installed SDK; the AUTH
WILL NOT WORK until the dashboard/capability config (Section 3) is done.

## 1. SDK API surface (verified against installed source, NOT guessed)
- `client.auth.signInWithIdToken(credentials: OpenIDConnectCredentials) async throws -> Session`
- `OpenIDConnectCredentials(provider: Provider, idToken: String, accessToken: String? = nil, nonce: String? = nil)`
- Provider enum: `OAuthProvider.google` / `OAuthProvider.apple` (conform to `Provider`).
  Use `OAuthProvider.google`, NOT a guessed `AuthClientOptions` type.
- For Google via native Supabase OAuth there's also
  `signInWithOAuth(provider:redirectTo:scopes:queryParams:launchFlow:)` but the
  ID-token exchange below is simpler (no URL-scheme redirect dance).

## 2. Service wrapper (SupabaseService.swift)
```swift
func signInWithGoogle(idToken: String, accessToken: String) async throws -> Session {
    try await client.auth.signInWithIdToken(credentials: OpenIDConnectCredentials(
        provider: OAuthProvider.google, idToken: idToken, accessToken: accessToken))
}
func signInWithApple(idToken: String, nonce: String?) async throws -> Session {
    try await client.auth.signInWithIdToken(credentials: OpenIDConnectCredentials(
        provider: OAuthProvider.apple, idToken: idToken, nonce: nonce))
}
```

## 3. LoginView — Google (GoogleSignIn SDK, already SPM-linked)
```swift
import GoogleSignIn
GIDSignIn.sharedInstance.signIn(withPresenting: rootVC) { result, error in
    guard let user = result?.user,
          let idToken = user.idToken?.tokenString,
          let accessToken = user.accessToken.tokenString else { return }
    appState.signInWithGoogle(idToken: idToken, accessToken: accessToken) { res in
        if case .failure(let e) = res { self.errorMessage = e.localizedDescription }
    }
}
```
GoogleSignIn auto-reads `CLIENT_ID` from `GoogleService-Info.plist`. That plist's
client ID must MATCH what you configure in Supabase's Google provider + Google
Cloud Console redirect URI (Section 5).

## 4. LoginView — Apple (AuthenticationServices, needs capability — Section 5)
```swift
import AuthenticationServices, CryptoKit
SignInWithAppleButton(.signIn) { request in
    let nonce = randomNonceString()
    currentNonce = nonce
    request.nonce = sha256(nonce)            // hashed nonce goes to Apple
    request.requestedScopes = [.fullName, .email]
} onCompletion: { result in
    signInWithApple(result: result)          // raw nonce -> Supabase
}
// onCompletion:
guard let cred = authorization.credential as? ASAuthorizationAppleIDCredential,
      let idToken = String(data: cred.identityToken!, encoding: .utf8) else { return }
appState.signInWithApple(idToken: idToken, nonce: currentNonce) { ... }
// helpers:
func randomNonceString() -> String { /* 32-char random */ }
func sha256(_ i: String) -> String { SHA256.hash(data: Data(i.utf8))... }
```
Apple expects the RAW nonce in `OpenIDConnectCredentials(nonce:)`; the hashed
one is in the id_token claim. Use CryptoKit `SHA256`.

## 5. MANDATORY config (code alone will NOT auth)
- **Xcode**: target AnglerGo → Signing & Capabilities → + Capability →
  **Sign in with Apple**. (Founder confuses the purple *folder group* with the
  blue *project* icon — click the BLUE icon, pick target under TARGETS, not Project.)
  Requires a paid Apple Developer Program membership or it red-errors.
- **Supabase dashboard → Authentication → Providers → Google**: enable, Client ID =
  the `GoogleService-Info.plist` CLIENT_ID (or a fresh OAuth client), and add
  redirect URI `https://<ref>.supabase.co/auth/v1/callback`.
- **Google Cloud Console**: that OAuth client → Authorized redirect URIs → add
  `https://<ref>.supabase.co/auth/v1/callback`.
- **Supabase → Providers → Apple**: enable (needs your Apple Services ID + the
  same Supabase callback; Apple requires domain verified + "Sign in with Apple").

## 6. Pitfalls
- P28a — `swiftc -parse` is SYNTAX-ONLY; it will NOT catch a wrong SDK type like
  `AuthClientOptions` (doesn't exist — the type is `AuthOptions`) or a missing
  `import Supabase`. For SDK-API doubts, grep the INSTALLED package under
  `~/Library/Developer/Xcode/DerivedData/AnglerGo-*/SourcePackages/checkouts/supabase-swift/Sources`.
- P28b — After dropping Firebase, `GIDSignIn.sharedInstance.handle(url)` in
  `application(_:open:options:)` is no longer needed (use `signIn(withPresenting:)`);
  removing it also kills the `OpenURLOptionsKey` deprecation warning.
- P28c — `SignInWithAppleButton` compiles WITHOUT the capability, but tapping it
  errors at runtime unless "Sign in with Apple" is enabled on the target.
- P28d — The `GoogleService-Info.plist` client ID is Firebase-era (project
  `fishgo-a98ae`); it still works for Supabase Google OAuth IF you wire Supabase's
  Google provider to that same client ID + add the Supabase callback to Google
  Cloud Console. If Google consent fails, that's a client-ID/redirect mismatch.
