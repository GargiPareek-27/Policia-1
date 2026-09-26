from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class AccountRead(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    assigned_doctor_id: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
