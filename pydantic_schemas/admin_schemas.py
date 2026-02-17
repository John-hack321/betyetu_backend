from pydantic import BaseModel 
from datetime import datetime
from typing import Optional

class AdminBase(BaseModel):
    admin_username : str

class CreateAdminRequest(AdminBase):
    admni_password: str
