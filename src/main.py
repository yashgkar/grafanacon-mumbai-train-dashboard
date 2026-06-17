import os
import random
import math
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

app = FastAPI(title="Mumbai Local Train Dummy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.environ.get("API_KEY", "mumbai-train-secret")

LINES = ["Central", "Western", "Harbour"]

STATIONS = {
    "CSTM":    "Chhatrapati Shivaji Maharaj Terminus",
    "Dadar":   "Dadar",
    "Andheri": "Andheri",
    "Borivali":"Borivali",
    "Thane":   "Thane",
    "Kurla":   "Kurla",
    "Bandra":  "Bandra",
    "Panvel":  "Panvel",
}

STATION_LINE = {
    "CSTM":    "Central",
    "Dadar":   "Central",
    "Thane":   "Central",
    "Kurla":   "Central",
    "Andheri": "Western",
    "Borivali":"Western",
    "Bandra":  "Western",
    "Panvel":  "Harbour",
}

DESTINATIONS_BY_LINE = {
    "Central": ["Thane", "Kalyan", "Kasara", "Khopoli", "Ambarnath"],
    "Western": ["Virar", "Dahanu Road", "Vasai Road", "Borivali", "Churchgate"],
    "Harbour": ["Panvel", "Belapur", "Nerul", "Vashi", "Andheri"],
}

INCIDENT_TYPES = [
    "signal_failure", "track_obstruction", "medical_emergency",
    "overhead_wire_fault", "flooding", "technical_fault", "crowd_control",
]

INCIDENT_DESCRIPTIONS = {
    "signal_failure":       "Signal failure causing delays between stations",
    "track_obstruction":    "Track obstruction being cleared by maintenance crew",
    "medical_emergency":    "Medical emergency on board, train held at station",
    "overhead_wire_fault":  "Overhead wire snag, pantograph inspection underway",
    "flooding":             "Waterlogging on tracks, slow movement section",
    "technical_fault":      "Technical fault in rake, crew attending",
    "crowd_control":        "Extreme crowd density, controlled boarding in effect",
}


def auth(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


def now_utc():
    return datetime.now(timezone.utc)


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": now_utc().isoformat()}


# ─── 1. Line Status ───────────────────────────────────────────────────────────
# Panel: Stat (color coded)
# Shape: flat array — one object per line
# Infinity: JSON → each row is one stat tile, color override via value mappings

@app.get("/lines/status")
def line_status(x_api_key: Optional[str] = Header(default=None)):
    auth(x_api_key)
    statuses = ["normal", "delay", "disrupted"]
    weights  = [0.65, 0.25, 0.10]
    result = []
    for line in LINES:
        status = random.choices(statuses, weights=weights)[0]
        result.append({
            "line":           line,
            "status":         status,
            # numeric so Grafana value mappings can color-code it
            "status_code":    {"normal": 0, "delay": 1, "disrupted": 2}[status],
            "delay_minutes":  random.randint(5, 20) if status == "delay" else
                              random.randint(20, 60) if status == "disrupted" else 0,
            "trains_running": random.randint(120, 160) if status == "normal" else
                              random.randint(80, 120),
            "updated_at":     now_utc().isoformat(),
        })
    return result


# ─── 2. Trains Running vs Halted ─────────────────────────────────────────────
# Panel: Bar gauge
# Shape: flat array — one object per line
# Infinity: JSON → fields: line, running, halted. Bar gauge on running/halted.

@app.get("/trains/count")
def train_count(x_api_key: Optional[str] = Header(default=None)):
    auth(x_api_key)
    result = []
    totals = {"Central": 180, "Western": 210, "Harbour": 95}
    for line in LINES:
        total   = totals[line]
        halted  = random.randint(2, 15)
        running = total - halted
        result.append({
            "line":          line,
            "running":       running,
            "halted":        halted,
            "total":         total,
            "pct_running":   round(running / total * 100, 1),
        })
    return result


# ─── 3. Crowd Heatmap ─────────────────────────────────────────────────────────
# Panel: Heatmap (Infinity time-series mode)
# Shape: ONE series per zone — array of {timestamp, value, zone}
# Infinity config:
#   - Format: Time series
#   - Timestamp field: timestamp
#   - Value field:     density
#   - Group by field:  zone   (creates one series per zone → heatmap rows)
# Grafana heatmap panel auto-buckets the timestamps into columns.

@app.get("/crowd/heatmap")
def crowd_heatmap(
    line: Optional[str] = Query(default=None, description="Filter by line: Central, Western, Harbour"),
    hours: int = Query(default=12, ge=1, le=24, description="How many past hours to return"),
    x_api_key: Optional[str] = Header(default=None),
):
    auth(x_api_key)

    zones = ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5"]

    # Rush hour peaks: 8-10 AM and 6-8 PM → higher density
    def crowd_density(hour_of_day: int, zone_idx: int) -> int:
        morning_rush = max(0, 80 - abs(hour_of_day - 9) * 18)
        evening_rush = max(0, 85 - abs(hour_of_day - 19) * 15)
        base = 20 + zone_idx * 5  # inner zones busier
        noise = random.randint(-8, 8)
        return min(100, max(0, base + morning_rush + evening_rush + noise))

    result = []
    base_time = now_utc().replace(minute=0, second=0, microsecond=0)

    for zone_idx, zone in enumerate(zones):
        for h in range(hours):
            ts = base_time - timedelta(hours=(hours - h - 1))
            result.append({
                "timestamp": ts.isoformat(),
                "zone":      zone,
                "density":   crowd_density(ts.hour, zone_idx),
                "line":      line if line else random.choice(LINES),
            })

    # Sort by timestamp ascending (Infinity time-series expects chronological order)
    result.sort(key=lambda x: x["timestamp"])
    return result


# ─── 4. AC vs Non-AC Frequency ───────────────────────────────────────────────
# Panel: Stat
# Shape: flat array — one row per (line × type) combination
# Infinity: JSON → stat panel, one tile per row

@app.get("/trains/frequency")
def train_frequency(x_api_key: Optional[str] = Header(default=None)):
    auth(x_api_key)
    base_freq = {
        "Central": {"AC": 4,  "Non-AC": 18},
        "Western": {"AC": 6,  "Non-AC": 22},
        "Harbour": {"AC": 2,  "Non-AC": 10},
    }
    result = []
    for line in LINES:
        for train_type in ["AC", "Non-AC"]:
            base = base_freq[line][train_type]
            result.append({
                "line":            line,
                "type":            train_type,
                "trains_per_hour": base + random.randint(-1, 1),
                "avg_interval_min": round(60 / (base + random.randint(-1, 1)), 1),
            })
    return result


# ─── 5. Real-time Incidents ──────────────────────────────────────────────────
# Panel: Table
# Shape: flat array — one row per incident
# Infinity: JSON → Table. severity drives Grafana color overrides.

@app.get("/incidents")
def incidents(
    line: Optional[str] = Query(default=None, description="Filter by line"),
    active_only: bool = Query(default=False, description="Return only unresolved incidents"),
    x_api_key: Optional[str] = Header(default=None),
):
    auth(x_api_key)
    severities = ["critical", "high", "medium", "low"]
    sev_weights = [0.10, 0.20, 0.40, 0.30]
    sev_code    = {"critical": 3, "high": 2, "medium": 1, "low": 0}

    n = random.randint(4, 10)
    result = []
    for i in range(n):
        inc_line = line if line else random.choice(LINES)
        inc_type = random.choice(INCIDENT_TYPES)
        sev      = random.choices(severities, weights=sev_weights)[0]
        resolved = random.random() < 0.4
        if active_only and resolved:
            continue
        started  = now_utc() - timedelta(minutes=random.randint(5, 180))
        result.append({
            "id":           i + 1,
            "line":         inc_line,
            "severity":     sev,
            "severity_code":sev_code[sev],     # numeric for Grafana thresholds
            "type":         inc_type,
            "description":  INCIDENT_DESCRIPTIONS[inc_type],
            "station":      random.choice(list(STATIONS.keys())),
            "started_at":   started.isoformat(),
            "duration_min": int((now_utc() - started).total_seconds() / 60),
            "resolved":     resolved,
        })

    result.sort(key=lambda x: x["severity_code"], reverse=True)
    return result


# ─── 6. Next Arrivals at Station ─────────────────────────────────────────────
# Panel: Table
# Shape: flat array — one row per upcoming train
# Infinity: JSON → Table. station param maps to Grafana $station variable.
# Valid stations: CSTM, Dadar, Andheri, Borivali, Thane, Kurla, Bandra, Panvel

@app.get("/arrivals")
def arrivals(
    station: str = Query(default="CSTM", description="Station code. One of: CSTM, Dadar, Andheri, Borivali, Thane, Kurla, Bandra, Panvel"),
    x_api_key: Optional[str] = Header(default=None),
):
    auth(x_api_key)

    if station not in STATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown station '{station}'. Valid: {', '.join(STATIONS.keys())}"
        )

    line = STATION_LINE[station]
    destinations = DESTINATIONS_BY_LINE[line]
    train_types  = ["Express", "Fast", "Slow"]
    type_weights = [0.3, 0.4, 0.3]
    platforms    = list(range(1, 7))
    statuses     = ["on_time", "on_time", "on_time", "delayed", "arriving"]

    result = []
    eta = 2
    for i in range(8):
        t_type    = random.choices(train_types, weights=type_weights)[0]
        is_ac     = t_type == "Express" and random.random() < 0.4
        status    = random.choice(statuses)
        delay_min = random.randint(3, 12) if status == "delayed" else 0
        result.append({
            "train_no":    f"{random.randint(10000,99999)}",
            "destination": random.choice(destinations),
            "line":        line,
            "platform":    random.choice(platforms),
            "eta_minutes": eta + delay_min,
            "type":        t_type,
            "is_ac":       is_ac,
            "status":      status,
            "delay_min":   delay_min,
            "coaches":     12 if t_type in ["Express", "Fast"] else 9,
        })
        eta += random.randint(3, 8)

    result.sort(key=lambda x: x["eta_minutes"])
    return result


# Lambda handler
handler = Mangum(app, lifespan="off")
