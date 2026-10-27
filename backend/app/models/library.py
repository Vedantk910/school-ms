"""Library: book catalogue, loans with due dates, daily fine computation."""
from datetime import date

from sqlmodel import Field, SQLModel

from app.db import Base


class Book(Base, table=True):
    __tablename__ = "book"
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    title: str
    author: str = Field(default="")
    isbn: str | None = Field(default=None)
    category: str = Field(default="general")
    total_copies: int = Field(default=1)
    available_copies: int = Field(default=1)


class Loan(Base, table=True):
    __tablename__ = "loan"
    id: int | None = Field(default=None, primary_key=True)
    book_id: int = Field(foreign_key="book.id", index=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    issued_date: date = Field(index=False)
    due_date: date
    returned_date: date | None = Field(default=None)
    fine_paise: int = Field(default=0)
    status: str = Field(default="issued", index=True)  # issued | returned | overdue
