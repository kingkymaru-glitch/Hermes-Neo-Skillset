"""Re-runnable ad-hoc probe: connect to the Luna-EDGE (or any) WS viewer and
count BINARY (video) vs TEXT (detection) messages. Catches the two classic
failure modes: 0-1 frame (flask_sock receive() blocking death) and no binary
(detector forgot to push frames to frame_q).

Run (venv active, engine started via /api/start first):
    python scripts/verify_stream.py
"""
import asyncio
import sys
import websockets


async def probe(url="ws://127.0.0.1:8000/ws", seconds=4):
    nbin = ntxt = 0
    t0 = asyncio.get_event_loop().time()
    async with websockets.connect(url) as ws:
        while asyncio.get_event_loop().time() - t0 < seconds:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1)
                if isinstance(msg, bytes):
                    nbin += 1
                else:
                    ntxt += 1
            except asyncio.TimeoutError:
                break
    print(f"binary(video) frames: {nbin}  text(detections): {ntxt}  over {seconds}s")
    if nbin < 10:
        print("WARN: too few binary frames -> WS handler likely dies after 1 frame (pitfall 1)")
    else:
        print("OK: video streaming continuously")
    if nbin == 0 and ntxt > 0:
        print("WARN: detections arrive but no video -> frame_q push missing (pitfall 5)")
    return nbin, ntxt


if __name__ == "__main__":
    u = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8000/ws"
    asyncio.run(probe(u))
