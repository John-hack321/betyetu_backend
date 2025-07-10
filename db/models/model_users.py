from sqlalchemy.orm import relationship
from sqlalchemy import Column , String , Integer , Enum , Boolean , ForeignKey , Text
from db.db_setup import Base
from db.models.mixins import TimeStamp


class User( TimeStamp , Base): # this base here is the declarative instance object from the db_setup file 
    __tablename__ = "users"

    id = Column(Integer , index = True , primary_key = True )
    email = Column(String(50) , nullable = False , unique = True )
    username = Column(String(50) , nullable = False )
    hashed_password = Column(String)

    workouts = relationship("Workout" , back_populates = "users")
    routines = relationship("Routine" , back_populates = "users")

class Workout( TimeStamp , Base):
    __tablename__ = "workouts"

    id = Column(Integer , index = True , primary_key = True )
    user_id = Column(Integer , ForeignKey("users.id") , nullable = False)
    name = Column(String , nullable = False )
    description = Column(Text , nullable = True)

    users = relationship("User" , back_populates = "workouts")

class Routine(TimeStamp , Base):
    __tablename__ = "routines"

    id = Column( Integer , primary_key = True , index = True )
    user_id = Column( Integer , ForeignKey("users.id") , nullable = False)
    name = Column(String , nullable = False)
    description = Column(Text , nullable = False )

    users = relationship("User" , back_populates = "routines")
    

# the relationship i want to believe will allow me to access users.routines and viceversa 



