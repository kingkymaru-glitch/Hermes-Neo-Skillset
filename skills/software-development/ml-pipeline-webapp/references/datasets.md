# Public Datasets for Predictive Maintenance

## AI4I 2020 Predictive Maintenance Dataset
- Source: UCI ML Repository (free)
- URL: https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip
- Size: 510KB, 10,000 rows
- Columns: UDI, Product ID, Type, Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min], Machine failure, TWF, HDF, PWF, OSF, RNF
- Failure events: 339 (Target=1)
- Use case: anomaly detection with labeled failures

## NASA CMAPSS (Turbofan Engine Degradation)
- Source: NASA Data Portal (free)
- URL: https://data.nasa.gov/docs/legacy/CMAPSSData.zip
- Size: 12MB, 4 sub-datasets (FD001-FD004)
- FD001: 100 engines, 1 operating condition, 1 fault mode, 20,631 cycles
- Columns: unit_id, time_cycles, op_setting_1-3, sensor_1-21
- RUL labels: separate file (remaining cycles at end of test)
- Use case: RUL prediction (run-to-failure sequences)

## ETDataset (Electricity Transformer)
- Source: GitHub (free)
- URL: https://github.com/zhouhaoyi/ETDataset
- Size: ~4 transformers, 2 years of data
- Columns: date, HUFL, HULL, MUFL, MULL, LUFL, LULL, OT
- OT = Oil Temperature (key health indicator)
- No failure events (normal operation only)
- Use case: anomaly detection on real transformer monitoring data

## Kaggle Datasets (require free account)
- Pump sensor data: https://www.kaggle.com/datasets/nphantawee/pump-sensor-data
- DGA transformer: https://www.kaggle.com/datasets/bantipatel20/dissolved-gas-analysis-of-transformer
- NASA CMAPSS mirror: https://www.kaggle.com/datasets/bishals098/nasa-cmapss-2-engine-degradation

## Dataset Selection Guide

| Goal | Best Dataset | Why |
|------|-------------|-----|
| Anomaly detection (labeled) | AI4I 2020 | 339 failures, clean schema |
| RUL prediction | NASA CMAPSS FD001 | Run-to-failure with RUL labels |
| Real transformer test | ETDataset | Actual monitoring data |
| General benchmark | AI4I + CMAPSS | Covers both anomaly + RUL |
