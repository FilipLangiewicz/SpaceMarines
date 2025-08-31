import re
from typing import Optional, Literal, List, Tuple
from fastapi import FastAPI, HTTPException, status, Query, Path, Body
from fastapi import Response
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, UTC, timedelta
from math import pi, sqrt, sin, cos, asin, atan2
from datetime import timezone
import dateutil.parser

app = FastAPI()


# <------------ MODELS ------------->

## Model for a satellite's orbit
class OrbitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    orbital_altitude: float = Field(..., gt=160, le=40000)
    inclination: float = Field(..., ge=0, le=180)
    raan: float = Field(..., ge=0, lt=360)

class Orbit(BaseModel):
    id: int
    name: str = Field(..., min_length=1, max_length=100)
    orbital_altitude: float = Field(..., gt=160, le=40000)
    inclination: float = Field(..., ge=0, le=180)
    raan: float = Field(..., ge=0, lt=360)

class OrbitListResponse(BaseModel):
    orbits: list[Orbit]
    total: int
    skip: int
    limit: int

## Model for a satellite
class SatelliteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    operator: str = Field(..., min_length=1, max_length=50)
    launch_date: datetime
    status: Optional[Literal["active", "inactive", "deorbited"]] = "active"
    initial_longitude: float = Field(..., ge=-180.0, le=180.0)
    orbit_id: int



    @field_validator("launch_date")
    @classmethod
    def date_must_be_in_past(cls, v: datetime) -> datetime:
        if v >= datetime.now(UTC):
            raise ValueError("Launch date must be in the past")
        return v

class Satellite(BaseModel):
    id: int
    name: str = Field(..., min_length=1, max_length=100)
    operator: str = Field(..., min_length=1, max_length=50)
    launch_date: datetime
    status: Optional[Literal["active", "inactive", "deorbited"]] = "active"
    initial_longitude: float = Field(..., ge=-180.0, le=180.0)
    orbit_id: int

    @field_validator("launch_date")
    @classmethod
    def date_must_be_in_past(cls, v: datetime) -> datetime:
        if v >= datetime.now(UTC):
            raise ValueError("Launch date must be in the past")
        return v

class SatelliteListResponse(BaseModel):
    satellites: List[Satellite]
    total: int
    skip: int
    limit: int

## Models for collisions response
class CollisionPosition(BaseModel):
    lat: float
    lon: float
    alt: float

class CollisionItem(BaseModel):
    satellite1: int
    satellite2: int
    time: str
    position: CollisionPosition

class CollisionsResponse(BaseModel):
    collisions: List[CollisionItem]


# <------------ DATA STORE ------------->

# template
# from sqlalchemy import create_engine
# from sqlalchemy.orm import declarative_base, sessionmaker, Session
# from sqlalchemy.pool import StaticPool
#
# engine = create_engine(
#     "sqlite:///:memory:",
#     connect_args={"check_same_thread": False},
#     poolclass=StaticPool,
# )
#
# SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
#
# Base = declarative_base()
#
#
# def get_db() -> Session:
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

orbits = {
    # 1: {"id": 1, "name": "Starlink-Shell-1", "orbital_altitude": 550.0, "inclination": 53.0, "raan": 120.0},
    # 2: {"id": 2, "name": "GPS-IIA", "orbital_altitude": 20200.0, "inclination": 55.0, "raan": 180.0}
}

satellites = {
    # 1: {"id": 1, "name": "Starlink-1", "operator": "SpaceX", "launch_date": datetime(2020, 5, 24), "status": "active", "initial_longitude": -75.0, "orbit_id": 1},
    # 2: {"id": 2, "name": "GPS-1", "operator": "USAF", "launch_date": datetime(1978, 2, 22), "status": "inactive", "initial_longitude": -120.0, "orbit_id": 2}
}


# <------------ GET /health ------------->
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# <------------ ORBITS ENDPOINTS ------------->

# <------------ GET /orbits/{id} ------------->
@app.get("/orbits/{id}", response_model=Orbit)
async def get_orbit(id: str = Path(...)):
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    id_int = int(id)

    if id_int not in orbits:
        raise HTTPException(status_code=404, detail="Orbit not found")
    return orbits[id_int]


# <------------ POST /orbits ------------->
@app.post("/orbits/", response_model=Orbit, status_code=status.HTTP_201_CREATED)
async def create_orbit(orbit: OrbitCreate):
    if any(o.name == orbit.name for o in orbits.values()):
        raise HTTPException(status_code=409, detail="Orbit name already exists")

    new_id = max(orbits.keys(), default=0) + 1
    new_orbit = Orbit(id=new_id, **orbit.model_dump())
    orbits[new_id] = new_orbit
    return new_orbit


# <------------ GET /orbits/ ------------->
@app.get("/orbits/", response_model=OrbitListResponse)
async def list_orbits(
    skip: str = Query("0"),
    limit: str = Query("10"),
    name: str | None = Query(None),
):
    if (not skip.isdigit()) or (not limit.isdigit()):
        raise HTTPException(status_code=400, detail="Invalid pagination parameters")
    skip = int(skip)
    limit = int(limit)
    if skip < 0 or limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination parameters"
        )

    filtered_orbits = list(orbits.values())
    if name:
        filtered_orbits = [
            o for o in filtered_orbits if name.lower() in o.name.lower()
        ]

    total = len(filtered_orbits)
    paginated = filtered_orbits[skip: skip + limit]

    return OrbitListResponse(
        orbits=paginated,
        total=total,
        skip=skip,
        limit=limit
    )


# <------------ PUT /orbits/{id} ------------->
@app.put("/orbits/{id}", response_model=Orbit)
async def update_orbit(
    id: str = Path(...),
    orbit_update: OrbitCreate = Body(...)
):
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format or invalid data")
    id = int(id)

    if id not in orbits:
        raise HTTPException(status_code=404, detail="Orbit not found")

    if any(o.name == orbit_update.name and o.id != id for o in orbits.values()):
        raise HTTPException(status_code=409, detail="Orbit name already exists")

    if not (160 < orbit_update.orbital_altitude <= 40000):
        raise HTTPException(status_code=400, detail="Invalid ID format or invalid data")
    if not (0 <= orbit_update.inclination <= 180):
        raise HTTPException(status_code=400, detail="Invalid ID format or invalid data")
    if not (0 <= orbit_update.raan < 360):
        raise HTTPException(status_code=400, detail="Invalid ID format or invalid data")

    updated_orbit = Orbit(id=id, **orbit_update.model_dump())
    orbits[id] = updated_orbit
    return updated_orbit


# <------------ DELETE /orbits/{id} ------------->
@app.delete("/orbits/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_orbit(id: str = Path(...)):
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    id_int = int(id)

    if id_int not in orbits:
        raise HTTPException(status_code=404, detail="Orbit not found")

    for sat in satellites.values():
        if sat.orbit_id == id_int:
            raise HTTPException(status_code=409, detail="Orbit in use by satellites")

    del orbits[id_int]


# <------------ SATELLITES ENDPOINTS ------------->

# <------------ POST /satellites/ ------------->
@app.post("/satellites/", response_model=Satellite, status_code=status.HTTP_201_CREATED)
async def create_satellite(sat_data: SatelliteCreate = Body(...)):
    if any(s.name == sat_data.name for s in satellites.values()):
        raise HTTPException(status_code=409, detail="Satellite name already exists")

    if not (sat_data.orbit_id > 0):
        raise HTTPException(status_code=400, detail="Invalid orbit ID format")

    if sat_data.orbit_id not in orbits:
        raise HTTPException(status_code=400, detail="Orbit not found")

    new_id = max(satellites.keys(), default=0) + 1
    satellite = Satellite(id=new_id, **sat_data.model_dump())
    satellites[new_id] = satellite
    return satellite


# <------------ GET /satellites/{id} ------------->
@app.get("/satellites/{id}", response_model=Satellite)
async def get_satellite(id: str = Path(...)):
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    sat_id = int(id)

    if sat_id not in satellites:
        raise HTTPException(status_code=404, detail="Satellite not found")

    return satellites[sat_id]


# <------------ GET /satellites/ ------------->
@app.get("/satellites/", response_model=SatelliteListResponse)
async def list_satellites(
    skip: str = Query("0"),
    limit: str = Query("10"),
    operator: Optional[str] = Query(None)
):
    if not skip.isdigit() or not limit.isdigit():
        raise HTTPException(status_code=400, detail="Invalid pagination parameters")

    skip = int(skip)
    limit = int(limit)

    if skip < 0 or limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Invalid pagination parameters")

    result = list(satellites.values())

    if operator:
        result = [
            s for s in result if operator.lower() in s.operator.lower()
        ]

    total = len(result)
    paginated = result[skip : skip + limit]

    return SatelliteListResponse(
        satellites=paginated,
        total=total,
        skip=skip,
        limit=limit
    )


# <------------ PUT /satellites/{id} ------------->
@app.put("/satellites/{id}", response_model=Satellite)
async def update_satellite(
    id: str = Path(...),
    satellite_update: SatelliteCreate = Body(...)
):
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format or invalid data")
    sat_id = int(id)

    if sat_id not in satellites:
        raise HTTPException(status_code=404, detail="Satellite not found")

    for s_id, sat in satellites.items():
        if s_id != sat_id and sat.name.lower() == satellite_update.name.lower():
            raise HTTPException(status_code=409, detail="Satellite name already exists")

    if satellite_update.orbit_id not in orbits:
        raise HTTPException(status_code=400, detail="Invalid orbit_id")

    updated_sat = Satellite(
        id=sat_id,
        **satellite_update.model_dump()
    )

    satellites[sat_id] = updated_sat
    return updated_sat


# <------------ DELETE /satellites/{id} ------------->
@app.delete("/satellites/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_satellite(id: str = Path(...)):
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    id_int = int(id)

    if id_int not in satellites:
        raise HTTPException(status_code=404, detail="Satellite not found")

    del satellites[id_int]
    return Response(status_code=204)


# <------------ GET /satellites/{id}/position ------------->
@app.get("/satellites/{id}/position")
async def get_satellite_position(
    id: str = Path(...),
    timestamp: Optional[str] = Query(None)
):
    # --- ID validation ---
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format or timestamp")
    sat_id = int(id)

    if sat_id not in satellites:
        raise HTTPException(status_code=404, detail="Satellite not found")
    sat = satellites[sat_id]

    # --- timestamp validation ---
    if timestamp is None:
        raise HTTPException(status_code=400, detail="Invalid ID format or timestamp")

    try:
        ts = dateutil.parser.isoparse(timestamp)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format or timestamp")

    if ts < sat.launch_date.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=400, detail="Timestamp before launch date")

    orbit = orbits.get(sat.orbit_id)
    if orbit is None:
        raise HTTPException(status_code=400, detail="Orbit not found")

    # --- orbital mechanics constants ---
    R_earth = 6371.0  # km
    mu = 398600.4418  # km^3/s^2
    a = R_earth + orbit.orbital_altitude
    T = 2 * pi * sqrt(a**3 / mu)
    omega = 2 * pi / T

    delta_t = (ts - sat.launch_date.replace(tzinfo=timezone.utc)).total_seconds()
    inclination_r = orbit.inclination * pi / 180.0
    raan_r = orbit.raan * pi / 180.0
    initial_longitude_r = sat.initial_longitude * pi / 180.0

    theta = (omega * delta_t + initial_longitude_r) % (2 * pi)
    lat_r = asin(sin(inclination_r) * sin(theta))
    lon_r = atan2(cos(inclination_r) * sin(theta), cos(theta)) + raan_r

    def wrap180(x: float) -> float:
        return ((x + 180) % 360) - 180

    lat = lat_r * 180.0 / pi
    lon = wrap180(lon_r * 180.0 / pi)
    alt = orbit.orbital_altitude

    return {"lat": lat, "lon": lon, "alt": alt}


# <------------ GET /collisions ------------->
@app.get("/collisions", response_model=CollisionsResponse)
async def get_collisions(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    precision: str | None = Query(None),
):
    if start_date is None or end_date is None:
        raise HTTPException(400, detail="Invalid date format or range")

    s = _parse_range_timestamp(start_date)
    e = _parse_range_timestamp(end_date)

    step = _parse_precision(precision)

    if e < s:
        raise HTTPException(400, detail="Invalid date format or range")

    s_rounded = _round_datetime_to_grid(s, step)
    e_rounded = _round_datetime_to_grid(e, step)

    time_grid = []
    current = s_rounded
    while current <= e_rounded:
        time_grid.append(current)
        current = current + step

    collisions: List[dict] = []
    min_sep_km = 0.01

    for ts in time_grid:
        active_positions = []
        for sat_id, sat in satellites.items():
            orbit = orbits.get(sat.orbit_id)
            if orbit is None:
                continue
            launch = sat.launch_date
            if launch.tzinfo is None:
                launch = launch.replace(tzinfo=timezone.utc)
            else:
                launch = launch.astimezone(timezone.utc)
            if ts < launch:
                continue
            ecef, geo = _compute_satellite_ecef_and_geo(sat, orbit, ts)
            active_positions.append((sat_id, ecef, geo))

        n = len(active_positions)
        if n < 2:
            continue

        for i in range(n - 1):
            id1, ecef1, geo1 = active_positions[i]
            for j in range(i + 1, n):
                id2, ecef2, geo2 = active_positions[j]
                dx = ecef1["x"] - ecef2["x"]
                dy = ecef1["y"] - ecef2["y"]
                dz = ecef1["z"] - ecef2["z"]
                dist = sqrt(dx * dx + dy * dy + dz * dz)
                if dist < min_sep_km:
                    sat1_id, sat2_id = sorted((id1, id2))
                    collisions.append({
                        "satellite1": sat1_id,
                        "satellite2": sat2_id,
                        "time": _format_utc(ts, step),
                        "position": geo1,
                    })

    collisions.sort(key=lambda it: (it["time"], it["satellite1"], it["satellite2"]))
    return CollisionsResponse(collisions=collisions)


# --- helper functions ---
def _parse_precision(value: str | None) -> timedelta:
    if value is None:
        return timedelta(minutes=1)
    m = re.fullmatch(r"(\d+)(ms|s|m|h|d)", value)
    if not m:
        raise HTTPException(400, detail="Invalid date format or range")
    n = int(m.group(1))
    if n <= 0:
        raise HTTPException(400, detail="Invalid date format or range")
    unit = m.group(2)
    mult = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400}
    return timedelta(seconds=n * mult[unit])

def _parse_range_timestamp(date_str: str) -> datetime:
    try:
        dt = dateutil.parser.isoparse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        raise HTTPException(400, detail="Invalid date format or range")


def _round_datetime_to_grid(dt: datetime, step: timedelta) -> datetime:
    ts = dt.timestamp()
    step_seconds = step.total_seconds()
    rounded = (ts // step_seconds) * step_seconds
    return datetime.fromtimestamp(rounded, tz=timezone.utc)

def _format_utc(dt: datetime, step: timedelta) -> str:
    if step < timedelta(seconds=1):
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    else:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _compute_satellite_ecef_and_geo(sat, orbit, ts: datetime) -> Tuple[dict, dict]:
    R_earth = 6371.0
    mu = 398600.4418
    a = R_earth + orbit.orbital_altitude
    T = 2 * pi * sqrt(a**3 / mu)
    omega = 2 * pi / T

    launch = sat.launch_date
    if launch.tzinfo is None:
        launch = launch.replace(tzinfo=timezone.utc)
    else:
        launch = launch.astimezone(timezone.utc)

    delta_t = (ts - launch).total_seconds()
    inclination_r = orbit.inclination * pi / 180.0
    raan_r = orbit.raan * pi / 180.0
    initial_longitude_r = sat.initial_longitude * pi / 180.0

    theta = (omega * delta_t + initial_longitude_r) % (2 * pi)
    lat_r = asin(sin(inclination_r) * sin(theta))
    lon_r = atan2(cos(inclination_r) * sin(theta), cos(theta)) + raan_r

    def _wrap180(x: float) -> float:
        return ((x + 180) % 360) - 180

    lat = lat_r * 180.0 / pi
    lon = _wrap180(lon_r * 180.0 / pi)
    alt = orbit.orbital_altitude

    lat_rad = lat * pi / 180.0
    lon_rad = lon * pi / 180.0
    r = R_earth + alt
    x = r * cos(lat_rad) * cos(lon_rad)
    y = r * cos(lat_rad) * sin(lon_rad)
    z = r * sin(lat_rad)

    return {"x": x, "y": y, "z": z}, {"lat": lat, "lon": lon, "alt": alt}
