# LAN Device Streaming (phone/S22 as camera or client)

## Symptom
User: "I'm on home WiFi, both devices, but nothing connects / not connected."

## Mechanion — CORRECT the user's intuition
Same-home-WiFi is the REQUIRED setup, not the problem. For a phone and Mac to talk,
both must be on the same LAN subnet. Different networks (phone on cellular, Mac on
WiFi) would fail. So "both on home WiFi" is correct and necessary.

## Real culprits (in order of likelihood)
1. **Stale hardcoded device IP.** The app pulls FROM the phone's IP-cam app
   (e.g. IP Webcam on Android serves `http://<phone-lan-ip>:8080/video`). That IP
   changes when the network changes (hotspot `172.20.10.x` vs home `192.168.x.x`).
   If the URI in the webapp still points at the OLD IP, the pull fails silently → blank.
   FIX: read the phone's current IP from the IP-cam app's on-screen URL, paste it into
   the Source URI field, Start.
2. **Server bound to 127.0.0.1.** If the PHONE is meant to open the control page
   (phone browser → Mac), the Mac server must `app.run(host="0.0.0.0", ...)`.
   `127.0.0.1` = localhost only, unreachable from the phone.
   (If the Mac only pulls FROM the phone and the Mac browser is the viewer, bind
   address matters less — the Mac initiates the connection.)
3. **Mac firewall** blocking the port.
4. **Phone app not running** / wrong port (not 8080).

## Quick checks from the Mac
- Reachability of phone stream:
  `curl -s -m 6 -o /dev/null -w "HTTP %{http_code} %{time_total}s\n" http://<phone-ip>:8080/video`
  A 200 (even if slow — MJPEG holds the connection open) = network path OK.
- Mac LAN IP: `ipconfig getifaddr en0`
- Phone opens Mac page at `http://<mac-lan-ip>:<port>` only if server binds 0.0.0.0.
