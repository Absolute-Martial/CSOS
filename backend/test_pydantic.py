from pydantic import BaseModel
from datetime import datetime

class T(BaseModel):
    x: datetime | None = None

print("Pydantic OK with union syntax")
