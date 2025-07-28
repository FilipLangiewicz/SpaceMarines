from typing import Optional, Literal, List

from fastapi import FastAPI, HTTPException, status, Query, Path, Body
from fastapi.openapi.models import Response
from pydantic import BaseModel, Field, validator, field_validator
from datetime import datetime, UTC

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
    orbit_id: int
    initial_longitude: float = Field(..., ge=-180.0, le=180.0)


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
    orbit_id: int
    initial_longitude: float = Field(..., ge=-180.0, le=180.0)

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


# <------------ DATA STORE ------------->

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
def health_check():
    return {"status": "healthy"}


# <------------ ORBITS ENDPOINTS ------------->

# <------------ GET /orbits/{id} ------------->
@app.get("/orbits/{id}", response_model=Orbit)
def get_orbit(id: str = Path(...)):
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    id_int = int(id)

    if id_int not in orbits:
        raise HTTPException(status_code=404, detail="Orbit not found")
    return orbits[id_int]


# <------------ POST /orbits ------------->
@app.post("/orbits/", response_model=Orbit, status_code=status.HTTP_201_CREATED)
def create_orbit(orbit: OrbitCreate):
    if any(o.name == orbit.name for o in orbits.values()):
        raise HTTPException(status_code=409, detail="Orbit name already exists")

    new_id = max(orbits.keys(), default=0) + 1
    new_orbit = Orbit(id=new_id, **orbit.model_dump())
    orbits[new_id] = new_orbit
    return new_orbit


# <------------ GET /orbits/ ------------->
@app.get("/orbits/", response_model=OrbitListResponse)
def list_orbits(
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
def update_orbit(
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
def delete_orbit(id: str = Path(...)):
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    id_int = int(id)

    if id_int not in orbits:
        raise HTTPException(status_code=404, detail="Orbit not found")

    for sat in satellites.values():
        if sat.orbit_id == id_int:
            raise HTTPException(status_code=409, detail="Orbit in use by satellites")

    del orbits[id_int]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# <------------ SATELLITES ENDPOINTS ------------->

# <------------ POST /satellites/ ------------->
@app.post("/satellites/", response_model=Satellite, status_code=status.HTTP_201_CREATED)
def create_satellite(sat_data: SatelliteCreate = Body(...)):
    if any(s.name == sat_data.name for s in satellites.values()):
        raise HTTPException(status_code=409, detail="Satellite name already exists")

    if not (sat_data.orbit_id > 0):
        raise HTTPException(status_code=400, detail="Invalid orbit ID format")

    if sat_data.orbit_id not in orbits:
        raise HTTPException(status_code=404, detail="Orbit not found")

    new_id = max(satellites.keys(), default=0) + 1
    satellite = Satellite(id=new_id, **sat_data.model_dump())
    satellites[new_id] = satellite
    return satellite


# <------------ GET /satellites/{id} ------------->
@app.get("/satellites/{id}", response_model=Satellite)
def get_satellite(id: str = Path(...)):
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    sat_id = int(id)

    if sat_id not in satellites:
        raise HTTPException(status_code=404, detail="Satellite not found")

    return satellites[sat_id]


# <------------ GET /satellites/ ------------->
@app.get("/satellites/", response_model=SatelliteListResponse)
def list_satellites(
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
def update_satellite(
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
@app.delete("/satellites/{id}", status_code=204)
def delete_satellite(id: str = Path(...)):
    if not id.isdigit() or int(id) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    id_int = int(id)

    if id_int not in satellites:
        raise HTTPException(status_code=404, detail="Satellite not found")

    del satellites[id_int]
    return Response(status_code=status.HTTP_204_NO_CONTENT)