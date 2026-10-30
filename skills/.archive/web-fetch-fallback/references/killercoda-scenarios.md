# Pulling KillerCoda / Katacoda scenario step content

KillerCoda scenario pages are SPAs. The HTML shell has no step text — it is
loaded client-side from a GitHub repo. To get the real content:

1. Fetch the page and read the `og:title` / `og:description` / `og:image` meta tags
   (the `og:image` banner often states the topic verbatim):
   `curl -sS -m 30 -L "https://killercoda.com/<org>/scenario/<scenario>"`

2. Find the source repo. Guess `<org>/killercoda-<scenario>` or search:
   `curl -sS -m 15 "https://api.github.com/search/repositories?q=<scenario>+killercoda"`

3. List the tree and pull the markdown steps:
   `curl -sS -m 15 "https://api.github.com/repos/<org>/<repo>/git/trees/main?recursive=1"`
   then read `raw.githubusercontent.com/<org>/<repo>/main/<scenario>/intro.md`,
   `stepN/stepN.md`, `finish.md`.

## Worked example — Edgenesis "Shifu Camera Demo"
- Repo: `Edgenesis/killercoda-shifu-demo`, folder `shifu-demo/`
- What it teaches: Shifu (CNCF, by Edgenesis) turns physical devices into
  Kubernetes-native HTTP resources. Each device gets a `deviceShifu` pod that
  translates the device's native protocol (ONVIF, Modbus, MQTT…) into plain HTTP,
  so apps call e.g. `GET /capture` instead of speaking the device protocol.
- Demo steps: (1) kubectl get nodes; (2) kubectl apply shifu_install.yml;
  (3) deploy a deviceShifu for a Hikvision camera (YAML apply); (4) port-forward
  the service and open `/capture` (photo) or `/stream` (live video).
- Relevance to MARU: a digital-twin "uniform ingestion" north star — normalize
  every physical source behind one HTTP/Kubernetes API instead of bespoke
  per-device connectors. MARU is currently client-side (Vite+React+Cesium+Supabase),
  not K8s, so Shifu is a reference pattern, not a drop-in.
