# File-source browser upload (loopback)

Localhost webapp limitation: the Python engine runs server-side and cannot open a
browser-picked `<input type="file">` File by its path. So "browse for a movie" must
UPLOAD the bytes to the Mac server first, then the engine reads the saved file.

## Server (Flask)
- `POST /api/upload` accepts `request.files['file']`, sanitizes the name
  (keep ext, drop path separators via `re.sub(r"[^A-Za-z0-9._-]", "_", base)`),
  rejects anything not in ALLOWED_EXT = (.mp4,.mov,.avi,.mkv,.webm),
  avoids clobber by appending `_N`, saves to `<app>/media/`, returns `{"ok":true,"path":abs}`.
- Start handler: if source.kind == "file", set `loop=True` (continuous feed).
- The saved path goes straight into `cv2.VideoCapture(path)` — same FileSource pipeline.

## Browser
- Source <select> change: if value=="file", hide the text URI input, show the file picker + a status line.
- `filePick.onchange`: `fetch('/api/upload', {method:'POST', body: new FormData().append('file', f)})`;
  on ok, store the returned path into the (hidden) `#uri` input; Start reads `#uri`.
- Guard: if source==file and `#uri` empty, refuse to start ("pick a video file first").

## Why loopback, not a drive path
The engine is localhost but still a separate process — a browser File handle is not a
filesystem path. Upload is instant on 127.0.0.1 and keeps the app fully offline.
