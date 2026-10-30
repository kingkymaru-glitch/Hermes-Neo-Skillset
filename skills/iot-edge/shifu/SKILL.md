---
name: shifu
description: Use when working with Shifu (Edgenesis CNCF IoT gateway), onboarding MQTT/ROS/HTTP devices, or mapping Shifu DeviceShifu endpoints into MARU / a Cesium digital-twin scene. Covers the verified protocol model, ConfigMap contract, ROS-via-rosbridge bridge, and the uniform-HTTP ingestion pattern.
---

# Shifu — Kubernetes-native protocol-agnostic IoT gateway

Shifu (Edgenesis, CNCF landscape) turns any physical device into a Kubernetes pod
("digital twin") that speaks plain HTTP. This skill is built from the actual repo
source (github.com/Edgenesis/shifu, main branch) — facts below are verified, not
hand-waved.

## When to use
- Onboarding MQTT / ROS1 / ROS2 / HTTP / TCP / socket / OPC UA / RTSP devices to a
  uniform HTTP plane.
- Mapping an existing DeviceShifu endpoint into MARU's Cesium twin scene.
- Answering "does Shifu support protocol X?" or "how does ROS plug in?".

## Core architecture (2 objects)
- `shifu` = a Kubernetes CRD (`shifu.edgenesis.io/v1alpha1`, kind `EdgeDevice`) that
  DECLARES a device exists and joins the cluster.
- `DeviceShifu` = a Kubernetes pod, the atomic unit of Shifu; "mainly contains the
  driver of the device and represents a device in the cluster. Or you can call it
  'digital twin' of the device." It IS the twin.

## The uniform HTTP contract (why it's "general")
Every DeviceShifu exposes the SAME HTTP surface regardless of the device's native
protocol:
- `instructions` — commands/reads you call (readWrite R or W). App sends HTTP,
  Shifu speaks native. App calls `http://<service>/<instructionName>`.
- `telemetries` — push streams the device emits (subscribe/poll); app subscribes to
  a TelemetryService instead of polling.
- `controlMsgs` — status signals the device reports.
The app ONLY speaks HTTP + K8s DNS. Protocol knowledge is trapped inside the
per-protocol driver; the app is ignorant of it.

## Built-in protocol drivers (verified from cmd/deviceshifu/*)
- Real driver binaries: `cmdhttp`, `cmdtcp`, `cmdsocket`, `cmdmqtt`, `cmdopcua`,
  `cmdlwm2m`, plus `cmdtemplate`. README also lists RTSP.
- Protocol settings structs (pkg/k8s/api/v1alpha1/edgedevice_types.go):
  - MQTTSetting: MQTTTopic, MQTTServerAddress, MQTTServerSecret, MQTTServerUserName, MQTTServerPassword
  - OPCUASetting: OPCUAEndpoint, SecurityMode, AuthenticationMode, Cert/Key, Username/Password, timeout
  - SocketSetting: encoding, bufferLength, networkType
  - TCPSetting: NetworkType, ListenPort
  - LwM2MSetting: endpointName, securityMode (None/DTLS), DTLSMode (PSK/RPK/X.509), cipherSuites, intervals
  - HTTPSetting (telemetryservice_types.go): username, password
- **NO native ROS/ROS1/ROS2 driver.** ROS plugs in via the CUSTOM driver path.

## How ROS (1/2) plugs in — the only extension point
- Run `rosbridge_suite` on the robot (RobotWebTools) → exposes ROS topics as
  WebSocket/JSON. Point a DeviceShifu at it with `protocol: HTTP` (or a small custom
  handler). Result: the robot becomes an ORDINARY DeviceShifu — identical to an MQTT
  sensor from the app's eyes. MARU never learns ROS.
- Custom driver = any HTTP service. Verified example
  (examples/deviceshifu/customized/humidity_detector/humidity-detector.go): a Go
  HTTP server on `:11111` exposing `/humidity` reading a `raw_data` file. deviceShifu
  `address: <host>:11111, protocol: HTTP` wraps it. Same shape works for rosbridge.

## The ConfigMap contract (the "device as API" — what MARU needs)
Real fragment (examples/httpDeviceShifu/deployment/http-deviceshifu-configmap.yaml):
```
data:
  driverProperties: |
    driverSku: HTTP Device
    driverImage: http-device:v0.0.1
  instructions: |
    instructions:
      status:
      info:
  telemetries: |
    telemetrySettings:
      telemetryUpdateIntervalInMilliseconds: 6000
      telemetryTimeoutInMilliseconds: 3000
    telemetries:
      device_health1:
        properties:
          instruction: status
          pushSettings:
            telemetryCollectionService: push-endpoint-1
```
- `instructions` = list of call names (for MQTT each maps to `protocolPropertyList.MQTTTopic`).
- `telemetries` = interval + per-telemetry `instruction` + optional `pushSettings`
  to a TelemetryService endpoint.
- DeviceShifu pod: image `edgehub/deviceshifu-<proto>-http:nightly`, containerPort
  8080, exposed via K8s Service (port 80 -> targetPort 8080), SA `edgedevice-sa`.

## TelemetryService (push sinks)
Separate CRD `TelemetryService` (pkg/.../telemetryservice_types.go):
TelemetryServiceSpec { telemetryServiceEndpoint, serviceSettings (HTTP/MQTT/SQL/MinIO),
customMetadata }. deviceShifu POSTs telemetry to push endpoints (verified Flask
example listens on :12345 at /endpoint1, /api1, /status, /info). For MARU you usually
POLL `instructions` over HTTP instead — simpler, no sink needed.

## Rerouting an EXISTING Shifu+rosbridge+ROS2 robot to MARU
- MARU just becomes ANOTHER HTTP client of the existing DeviceShifu. Robot, rosbridge,
  Shifu unchanged. All MARU needs = the DeviceShifu ConfigMap contract (service name,
  instruction list R/W, JSON shape). No robot-side knowledge.
- 3 things NOT inside the robot (add once, in front):
  1. Network path — DeviceShifu is cluster-internal; browser MARU needs ingress/
     gateway/tunnel to reach it.
  2. Auth boundary — DeviceShifu default "No authentication required." Pair with
     MARU's Supabase auth so only logged-in users can POST control commands.
  3. Control instructions (maybe) — if only R instructions exist, add W instructions
     to the ConfigMap (data change, no code change).
- Proof without robot: point MARU's Cesium scene at the existing `/state` instruction
  using only the ConfigMap contract → render moving twin. Zero robot/Shifu changes.

## MARU fit / pitfalls
- Each physical thing → one DeviceShifu pod = one twin endpoint. MARU's Cesium scene
  polls `http://<deviceshifu>/instruction` like any REST source (same as Supabase/
  AISStream). No ROS/MQTT code enters MARU.
- Shifu runs "from Raspberry Pi to edge clusters to cloud" — matches MARU's edge
  nature; translator can live on the robot's own edge box.
- GOTCHAS: (1) no prebuilt ROS driver — needs rosbridge+custom handler. (2) DeviceShifu
  default has NO auth — never expose control to the internet without a gate. (3)
  Service is cluster-internal — needs ingress for external/browser access.

## Verification (if facts need re-checking)
Web search is often disabled — fetch source directly:
```
curl -sS https://raw.githubusercontent.com/Edgenesis/shifu/main/README.md
curl -sS https://raw.githubusercontent.com/Edgenesis/shifu/main/pkg/k8s/api/v1alpha1/edgedevice_types.go
curl -sS https://raw.githubusercontent.com/Edgenesis/shifu/main/examples/httpDeviceShifu/deployment/http-deviceshifu-configmap.yaml
curl -sS https://raw.githubusercontent.com/Edgenesis/shifu/main/examples/deviceshifu/customized/humidity_detector/humidity-detector.go
```
For ROS bridge: `curl -sS https://raw.githubusercontent.com/RobotWebTools/rosbridge_suite/main/README.md`
