# Mac Sensor Agent — Live Mac Health Monitoring

## Architecture

```
Mac (agent.py via tmux, invisible)
  └─ samples CPU/mem/disk/battery/temp every 2s via psutil
  └─ POSTs to backend /api/mac-reading
  └─ detects sleep (gap > 30s), sends wake event on resume
Backend (new /api/mac-reading + /api/mac-stream endpoints)
  └─ stores readings in rolling deque (maxlen=500)
  └─ resets anomaly state on wake event
  └─ GET /api/mac-stream returns buffer for frontend
Frontend (new "Mac Sensors" source option)
  └─ polls /api/mac-stream every 2s (not WebSocket)
  └─ chart renders raw sensor values
  └─ anomaly detection activates after training on collected data
```

## What the Agent Samples (13 metrics)

| Metric | psutil source | Typical range |
|--------|--------------|---------------|
| cpu_percent | cpu_percent() | 0-100% |
| cpu_freq_mhz | cpu_freq() | 800-3228 |
| mem_percent | virtual_memory().percent | 0-100% |
| mem_used_gb | virtual_memory().used | 0-16 |
| mem_available_gb | virtual_memory().available | 0-16 |
| disk_percent | disk_usage('/').percent | 0-100% |
| disk_free_gb | disk_usage('/').free | 0-500 |
| battery_percent | sensors_battery().percent | 0-100 |
| battery_plugged | sensors_battery().power_plugged | 0/1 |
| battery_secs_left | sensors_battery().secsleft | 0-100000 |
| process_count | len(pids()) | 0-800 |
| temp_c | sensors_temperatures() | varies |
| net_sent_mb | net_io_counters().bytes_sent | 0-GBs |
| net_recv_mb | net_io_counters().bytes_recv | 0-GBs |
| uptime_hours | time.time() - boot_time() | 0-1000+ |

## Sleep/Wake Detection

- Agent tracks time since last sample
- Gap > 30 seconds = considered asleep
- On wake: POSTs `{"event": "wake"}` to backend
- Backend clears anomaly state on wake (no false alarms after lid-open)

## Frontend Polling Pattern

Poll /api/mac-stream every 2 seconds when source is mac_sensors. Chart renders raw sensor values. Anomaly detection activates after training on collected data.

## Running the Agent

```bash
tmux new-session -d -s mac-agent 'cd ~/LUNAV-Intel-M/backend && .venv/bin/python app/mac_agent.py'

curl -s http://localhost:8001/api/mac-stream | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Buffer: {d[\"count\"]} readings')"

# Stop
tmux kill-session -t mac-agent
```

## Memory & Performance

- Agent: ~33MB RAM, posts every 2 seconds
- Backend buffer: 500 readings max (~16 min at 2s interval)
- No training needed for visualization — raw data streams immediately
- Anomaly detection requires training after data collection
