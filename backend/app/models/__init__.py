"""Register all table models on SQLModel.metadata. Import order matters:
core -> people -> academic -> fees -> audit (foreign keys resolve by table name)."""
from app.models.core import Board, AcademicYear, ClassSection, Subject, SubjectScheme, Teacher, Holiday
from app.models.people import User, Guardian, Student, Enrollment, Admission
from app.models.academic import Attendance, Exam, ExamPaper, Mark, Result
from app.models.fees import (
    FeeHead, Bill, BillLine, Payment, Receipt, ReceiptSequence,
    ModelRegistry, Insight, OutboxMessage,
)
from app.models.audit import AuditLog

__all__ = [
    "Board", "AcademicYear", "ClassSection", "Subject", "SubjectScheme", "Teacher", "Holiday",
    "User", "Guardian", "Student", "Enrollment", "Admission",
    "Attendance", "Exam", "ExamPaper", "Mark", "Result",
    "FeeHead", "Bill", "BillLine", "Payment", "Receipt", "ReceiptSequence",
    "ModelRegistry", "Insight", "OutboxMessage",
    "AuditLog",
]
