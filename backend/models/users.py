from db.base import Base
from sqlalchemy import TEXT, Column, Integer


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(TEXT, nullable=False)
    email = Column(TEXT, unique=True, index=True, nullable=False)
    congnito_sub = Column(TEXT, unique=True, index=True, nullable=False)
