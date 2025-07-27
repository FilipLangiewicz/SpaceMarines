from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime


app = FastAPI()

# <------------ MODELS ------------->

## Model for a satellite's orbit
class Orbit(BaseModel):
    id: int
    name: str
    orbital_altitude: float
    inclination: float
    raan: float

## Model for a satellite
class Satellite(BaseModel):
    id: int
    name: str
    operator: str
    launch_date: datetime
    status: str
    initial_longitude: float
    orbit_id: int  # reference to Orbit.id



# <------------ GET /health ------------->
@app.get("/health")
def health_check():
    return {"status": "healthy"}