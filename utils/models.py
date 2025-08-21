from pydantic import BaseModel
from typing import Literal

class Entry(BaseModel):
    engine: Literal["PostgreSQL", "MariaDB"]
    instance_type: str
    region: str
    multi_az: Literal["Oui", "Non"]
    start: str
    end: str

class EC2Entry(BaseModel):
    instance_type: str
    region: str

class EC2ExtendedEntry(BaseModel):
    instance_type: str
    vcpus: int
    memory_gb: float
    region: str