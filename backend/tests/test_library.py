"""Library: catalogue search, checkout/return with copy availability, late fine.

Books are seeded via a direct ORM session (the library router is intentionally
loan-centric, not a catalogue-admin surface); loans flow through the API.
"""
from sqlmodel import Session, select

from app.db import engine
from app.models.library import Book
from tests.conftest import _auth


def _make_book(code: str, copies: int) -> int:
    with Session(engine) as s:
        b = Book(code=code, title=f"Book {code}", author="Test",
                 total_copies=copies, available_copies=copies)
        s.add(b)
        s.commit()
        s.refresh(b)
        return b.id


def test_search_books_returns_availability(client, admin_token):
    bid = _make_book("LIB-001", 2)
    r = client.get("/api/v1/library/books?q=LIB-001",
                   headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200
    rows = [x for x in r.json() if x["id"] == bid]
    assert rows and rows[0]["available_copies"] == 2


def test_checkout_decrements_copy_and_blocks_third(client, admin_token):
    _make_book("LIB-002", 2)
    auth = _auth(admin_token["access_token"])
    for sid in (1, 2):
        r = client.post("/api/v1/library/books/checkout",
                        json={"student_id": sid, "book_code": "LIB-002"}, headers=auth)
        assert r.status_code == 200, r.text
        assert r.json()["loan_id"]
    r3 = client.post("/api/v1/library/books/checkout",
                     json={"student_id": 3, "book_code": "LIB-002"}, headers=auth)
    assert r3.status_code == 400  # no copies left


def test_duplicate_open_loan_rejected(client, admin_token):
    _make_book("LIB-003", 3)
    auth = _auth(admin_token["access_token"])
    client.post("/api/v1/library/books/checkout",
                json={"student_id": 1, "book_code": "LIB-003"}, headers=auth)
    r = client.post("/api/v1/library/books/checkout",
                    json={"student_id": 1, "book_code": "LIB-003"}, headers=auth)
    assert r.status_code == 400  # active loan already exists


def test_late_return_fine_and_copy_restore(client, admin_token):
    _make_book("LIB-004", 1)
    auth = _auth(admin_token["access_token"])
    cko = client.post("/api/v1/library/books/checkout",
                      json={"student_id": 1, "book_code": "LIB-004", "due_days": 21},
                      headers=auth).json()
    # issued 2026-06-30 + 21 days -> due 2026-07-21; return 3 days late
    r = client.post(f"/api/v1/library/loans/{cko['loan_id']}/return",
                    params={"return_date": "2026-07-24"}, headers=auth)
    assert r.status_code == 200
    assert r.json()["fine_paise"] == 6000  # 3 x 2000
    assert r.json()["fine_rs"] == "60.00"
    ontime = client.post("/api/v1/library/books/checkout",
                         json={"student_id": 2, "book_code": "LIB-004"}, headers=auth)
    assert ontime.status_code == 200  # copy restored
    ontime_loan = ontime.json()["loan_id"]
    r2 = client.post(f"/api/v1/library/loans/{ontime_loan}/return",
                     params={"return_date": "2026-07-05"}, headers=auth)
    assert r2.json()["fine_paise"] == 0  # early return, no fine


def test_parent_lists_own_loans_only(client, parent_token, admin_token):
    _make_book("LIB-005", 2)
    auth = _auth(admin_token["access_token"])
    client.post("/api/v1/library/books/checkout",
                json={"student_id": 1, "book_code": "LIB-005"}, headers=auth)
    ok = client.get("/api/v1/library/loans?student_id=1",
                    headers=_auth(parent_token["access_token"]))
    assert ok.status_code == 200 and len(ok.json()) == 1
    denied = client.get("/api/v1/library/loans?student_id=2",
                        headers=_auth(parent_token["access_token"]))
    assert denied.status_code == 403
    cko = client.post("/api/v1/library/books/checkout",
                      json={"student_id": 1, "book_code": "LIB-005"},
                      headers=_auth(parent_token["access_token"]))
    assert cko.status_code == 403  # parents can't check out
