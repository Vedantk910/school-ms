"""Transport: routes, ordered stops with per-stop charges, vehicles, stop-charge assignments."""
from datetime import date

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, Date, Integer, Text, UniqueConstraint

from app.db import Base


class Route(Base, table=True):
    __tablename__ = "route"
    id: int | None = Field(default=None, primary_key=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    name: str
    level: int  # which class level this route primarily serves
    direction: str = Field(default="inbound")  # inbound | outbound

    __table_args__ = (UniqueConstraint("year_id", "name", "direction"),)


class RouteStop(Base, table=True):
    __tablename__ = "route_stop"
    id: int | None = Field(default=None, primary_key=True)
    route_id: int = Field(foreign_key="route.id", index=True)
    sequence: int  # 1-based stop order along the route
    stop_name: str
    address: str = Field(default="")
    charge_paise: int = Field(default=0)

    __table_args__ = (UniqueConstraint("route_id", "sequence"),)


class Vehicle(Base, table=True):
    __tablename__ = "vehicle"
    id: int | None = Field(default=None, primary_key=True)
    registration_masked: str = Field(index=True)  # e.g. "MH-12-****-34"
    driver_name: str
    driver_phone: str = Field(default="")
    capacity: int = Field(default=40)
    route_id: int | None = Field(default=None, foreign_key="route.id")


class TransportAssignment(Base, table=True):
    """A student riding a specific stop; charge defaults to the stop's charge_paise."""
    __tablename__ = "transport_assignment"
    id: int | None = Field(default=None, primary_key=True)
    route_stop_id: int = Field(foreign_key="route_stop.id", index=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    monthly_charge_paise: int = Field(default=0)
    status: str = Field(default="active", index=True)  # active | inactive

    __table_args__ = (UniqueConstraint("route_stop_id", "student_id"),)
