"""Minimal Luna-EDGE-style detect skeleton — copy and modify.
4 swappable layers: Source / Detector / GeoAdapter / Sink.
Off-line-first: no cloud imports at the core.
"""
from abc import ABC, abstractmethod
import numpy as np

# ---- Detection dataclass (single source of truth) ----
from dataclasses import dataclass
@dataclass
class Detection:
    ts: float
    cls: str
    conf: float
    bbox: list          # [x, y, w, h]
    lat=None; lon=None; elev=None; heading=None

# ---- Layer 1: Source ----
class Source(ABC):
    def __init__(self, uri): self.uri=uri
    @abstractmethod
    def read(self): ...   # -> (frame, ts) or None

class WebcamSource(Source):
    def __init__(self, uri):
        import cv2; self.cap=cv2.VideoCapture(int(uri) if str(uri).isdigit() else uri)
        if not self.cap.isOpened(): raise RuntimeError("webcam not opened")
    def read(self):
        import time; ok,f=self.cap.read()
        return (f, time.time()) if ok else None

# ---- Layer 2: Detector (source-blind) ----
class Detector(ABC):
    @abstractmethod
    def infer(self, frame): ...

class YoloDetector(Detector):
    def __init__(self, skill="coco"):
        from ultralytics import YOLO
        self.model = YOLO("yolov8n.pt" if skill=="coco" else f"skills/{skill}.pt")
    def infer(self, frame):
        res=self.model(frame, conf=0.35, verbose=False)[0]
        out=[]
        for b in res.boxes:
            x1,y1,x2,y2=b.xyxy[0].tolist()
            out.append(Detection(0.0, self.model.names[int(b.cls[0])],
                                 float(b.conf[0]), [x1,y1,x2-x1,y2-y1]))
        return out

# ---- Layer 3: Geo (optional) ----
class NoneGeo(ABC):
    def attach(self, d, ts): return d

# ---- Layer 4: Sink ----
class StdoutSink(ABC):
    def emit(self, dets):
        for d in dets: print(d.cls, round(d.conf,2), [round(v,1) for v in d.bbox])

# ---- Wiring ----
def run(source: Source, skill="coco"):
    det=YoloDetector(skill); geo=NoneGeo(); sink=StdoutSink()
    while True:
        item=source.read()
        if item is None: break
        f,ts=item; ds=det.infer(f)
        for d in ds: d.ts=ts
        ds=[geo.attach(d,ts) for d in ds]
        sink.emit(ds)

if __name__=="__main__":
    run(WebcamSource("0"))
