"""SQLAlchemy declarative base for LF models.

Provides the common DeclarativeBase parent class for all ORM model classes in lfdata.

Usage example:
    from lfdata.model.base import Base

    # Model classes inherit from Base:
    # class MyModel(Base): ...
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models.

    Acts as the declarative metadata registry for lfdata database tables.
    """

    pass
