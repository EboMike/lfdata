"""SQLAlchemy declarative base model for lflive.

This module defines the shared declarative base class for all persistent
database models in the lflive service.

Usage example:
    from lflive.models.base import Base

    class MyModel(Base):
        __tablename__ = 'my_table'
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all lflive SQLAlchemy entities.

    Attributes:
        None.
    """

    pass

