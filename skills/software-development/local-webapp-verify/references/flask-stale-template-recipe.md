# Flask stale-template reproduction & fix (real session)

## Symptom
User: "i dont see any changes that u did" at localhost:8000, even though
templates/index.html and templates/learn.html were edited and committed.

## Diagnosis
Running server (PID from `python app.py`, `debug=False`) had the OLD compiled
Jinja2 template in memory. `curl http://localhost:8000/ | grep learnBtn.onclick`
returned the OLD handler line; the file on disk had the new one. Restart fixed it.

## Confirmed fix
```python
app = Flask(__name__)
app.jinja_env.auto_reload = True           # recompile templates each request
app.config["TEMPLATES_AUTO_RELOAD"] = True # Flask-level flag
```
After adding this, edits to templates show without restart. debug stays False.

## Repro loop (agent-runnable)
```
# stale server:
curl -s http://localhost:8000/ | grep -c "window.location.href = '/learn'"   # 0 = stale
# after restart or with auto_reload:
curl -s http://localhost:8000/ | grep -c "window.location.href = '/learn'"   # 1 = served
```

## Port/process helpers
```
lsof -nP -iTCP:8000 -sTCP:LISTEN        # find PID holding the port
kill <PID> && sleep 1                    # free it
.venv/bin/python app.py > launch.log 2>&1 &   # relaunch in venv
```

## Browser-tool block
`browser_exec` refuses localhost/private IPs ("URL targets a private or internal
address"). Verify UI via curl + grep, and frontend save paths via a Python
`requests` script that sends the same JSON/base64 the JS `fetch` would.
