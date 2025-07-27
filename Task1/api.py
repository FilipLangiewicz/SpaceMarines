from fastapi import FastAPI, HTTPException, status, Query, Path, Body
from pydantic import BaseModel, Field
from datetime import datetime


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
class Satellite(BaseModel):
    id: int
    name: str
    operator: str
    launch_date: datetime
    status: str
    initial_longitude: float
    orbit_id: int  # reference to Orbit.id


# <------------ DATA STORE ------------->

orbits = {
    # 1: {"id": 1, "name": "Starlink-Shell-1", "orbital_altitude": 550.0, "inclination": 53.0, "raan": 120.0},
    # 2: {"id": 2, "name": "GPS-IIA", "orbital_altitude": 20200.0, "inclination": 55.0, "raan": 180.0}
}


# <------------ GET /health ------------->
@app.get("/health")
def health_check():
    return {"status": "healthy"}


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