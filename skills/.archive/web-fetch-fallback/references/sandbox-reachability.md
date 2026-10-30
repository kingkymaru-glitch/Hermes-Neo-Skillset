# Sandbox reachability — external connections are inconclusive from the sandbox

When reproducing a connection to an EXTERNAL host (WebSocket, HTTP API, DB, MQTT,
git remote), a failure from the **agent sandbox** is OFTEN INCONCLUSIVE: the
sandbox may be network-firewalled while the user's own machine reaches the host
fine.

## Signals that are NOT proof of a broken user environment
- `WebSocket` close with code 1006 / "could not reach host"
- `curl` connection timeout
- `python socket.gaierror` / `NameResolutionError` on DNS lookup
- `ECONNREFUSED` / `ENOTFOUND` from a node client

## Pattern to follow
1. Run the repro from the sandbox to learn what you can (env/key validity, local
   config, code path, exact error string).
2. Explicitly test whether the sandbox itself can reach the host before
   interpreting a connection failure:
   `python3 -c "import socket;print(socket.gethostbyname('host'))"`
   `curl -sS -m 8 -I https://host/`
3. If the sandbox CAN'T reach the host, say so plainly and ask the user for the
   Mac-side signal — don't declare the connection dead. Give them a one-shot
   command (e.g. open the app with `?aisdebug=1` and paste the `[aisstream]` console
   lines, or run a `node` WebSocket probe in their Terminal) or ask them to paste
   the on-screen status/error the app shows.
4. Act on the Mac-side signal, which is the decisive evidence.

## MARU examples where this mattered
- Supabase `ENOTFOUND eobkcsxwwpszybwpqqy.supabase.co`: first (wrongly) diagnosed
  as a sandbox firewall; the real cause was a typo'd project ref (the char `b`
  should have been `z`). The true proof came from the user's Mac running the
  audit, which returned the corrected ref.
- AISStream `wss://stream.aisstream.io/v0/stream`: sandbox got code 1006 / 0 frames;
  sandbox also failed `curl` + DNS socket to that host, so the 1006 was
  inconclusive. Decisive diagnosis required the user's browser console / Mac-side
  node probe (their machine reaches the internet normally).

## Takeaway
Sandbox CAN reach some hosts (it resolved the corrected Supabase ref and ran the
6/6 audit). So "sandbox failure" is a per-host fact, not a general rule. Always
state the sandbox's reachability for the specific host before concluding.
