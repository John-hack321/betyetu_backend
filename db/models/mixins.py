from datetime import datetime

from sqlalchemy import Column , DateTime
from sqlalchemy.orm import declarative_mixin

@declarative_mixin
class TimeStamp:
    created_at = Column(DateTime , default=datetime.utcnow , nullable = False)
    updated_at = Column(DateTime , default=datetime.utcnow , nullable = False)

# this will allow us to know at what time each object was created and when it was updated