# ARRAS / Air Selangor Reference

## Opportunity
- Client: Syarikat Air Selangor
- RFI: Provision of Unmanned Sediment Monitoring System for Service Water Reservoirs
- Project name: ARRAS (Augmented Reservoir Residue & Accumulation Surveillance)
- Document number: CR/SSR/AS/ARRAS/001
- Status: RFI response draft
- Folder: ~/Desktop/AIR SEL

## Naming convention
- Primary response name: ARRAS
- SS Rover internal platforms: WAVE, LunaV, ROVER-KIT
- ARRAS modules map to internal platforms:
  - ARRAS: Command Centre → WAVE
  - ARRAS: Digital Twin → LunaV
  - ARRAS: Predictive Analytics → WAVE
  - ARRAS: Anomaly Detection → WAVE
  - ARRAS: Prescriptive Library → WAVE
  - ARRAS: Source Protection → WAVE
  - ARRAS: Spatial Inspection → LunaV
  - ARRAS: Sensor Framework → ROVER-KIT
  - ARRAS: Edge Communications → ROVER-KIT

## Pilot scope
- 10 service reservoirs
- 18 months
- 1 FIFISH ROV with MBES/sonar
- 1x DJI Matrice RTK 350 Drone Lidar
- 10x RasPi5 Field Agent Units
- USBL acoustic positioning
- Live-view sonar scanning

## Scale-up scope
- Up to 1600+ reservoirs and other water assets
- 3x FIFISH ROV
- 3x DJI Matrice RTK 350
- Per-node subscription + platform licensing + managed services

## Field agent unit
- Compute: Raspberry Pi 5
- Sensors: camera, light, depth, turbidity, interface probe, temperature, ambient, gyrometer, GPS
- Comms: ROVER-KIT GSM + LoRa
- Power: battery + solar panel + charge controller
- Enclosure: waterproof IP68
- Storage: 7-day rolling local buffer
- Data policy: end-of-day summary; anomaly-triggered alert + 5-day raw push; overwrite after 7-day average if clean

## Site challenges
- GPS-denied enclosed concrete reservoirs
- Weak/no mobile coverage
- No permanent power at some sites
- Working at height / confined access
- Lightning and surge exposure

## Cost sections
- Section split: POC vs Full Scale Deployment
- POC quantities: 1 ROV, 1 Drone Lidar, 10 field agents, 1 USBL
- Full-scale quantities: 3 ROVs, 3 Drone Lidars, 1600 field agents, 3 USBL

## AI layer
- YOLO visual inspection for defects and anomalies from camera/sonar feeds
- RAG system trained on Air Selangor operational processes, maintenance standards, and asset records

## Prior POC
- Effingham Service Reservoir, March 2026
- FIFISH E-Master Navi with Q-DVL and Cerulean sonar
- Two 40-minute dives, 2170 + 2004 data points
- ~2-3 cm average sediment thickness estimated visually
- GPS instability identified as primary limitation

## Key contacts
- Ir. Ts. Kamarul Hisham Kamaruzaman — Chief Business Officer
- Syamsul Nizam Azmee — Managing Director
- Mohammad Farith Johari — Chief Operation Officer
