"""Staff HR + light payroll: profiles, leave lifecycle, one computed monthly sheet.

Per decision D3 this is NOT a full payroll engine — just staff data + leave
inputs and a single computed monthly net-pay figure."""
from datetime import date

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, Date, UniqueConstraint

from app.db import Base


class StaffMember(Base, table=True):
    __tablename__ = "staff_member"
    id: int | None = Field(default=None, primary_key=True)
    staff_code: str = Field(index=True, unique=True)
    name: str
    category: str = Field(default="teaching")  # teaching | non_teaching
    designation: str = Field(default="")
    joined_date: date = Column(Date, nullable=False)
    monthly_base_paise: int = Field(default=0)
    monthly_allowances_paise: int = Field(default=0)
    active: bool = Field(default=True)


class LeaveRecord(Base, table=True):
    __tablename__ = "leave_record"
    id: int | None = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff_member.id", index=True)
    leave_type: str = Field(default="casual")  # casual | sick | unpaid
    from_date: date = Column(Date, nullable=False)
    to_date: date = Column(Date, nullable=False)
    days: int = Field(default=1)
    status: str = Field(default="pending", index=True)  # pending | approved | rejected
    applied_date: date = Column(Date, nullable=False)


class PayrollEntry(Base, table=True):
    """One computed net-pay figure per staff-member per month."""
    __tablename__ = "payroll_entry"
    id: int | None = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff_member.id", index=True)
    month: str = Field(index=True)  # 'YYYY-MM'
    base_paise: int = Field(default=0)
    allowances_paise: int = Field(default=0)
    deductions_paise: int = Field(default=0)
    unpaid_days: int = Field(default=0)
    net_paise: int = Field(default=0)
    status: str = Field(default="computed")  # computed | finalised

    __table_args__ = (UniqueConstraint("staff_id", "month"),)
