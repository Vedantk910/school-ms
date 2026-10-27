"""Deterministic synthetic seed for the MSBSHSE 550-student school.

Design goals (decision D8):
- No real PII; fully reproducible (``rng = np.random.default_rng(42)``).
- Correlated risk signal: attendance drop -> late fees -> low marks -> withdrawal.
  This gives the ML features real learnable structure and SHAP real features to show.
- 5 academic years (2021-22 .. 2025-26), as-of 2026-06-30, so a clean temporal
  train/eval split exists (train 2021-24, eval 2025-26).

Volume targets: ~240k attendance rows, ~45k marks, ~32k bills, ~35k payments.

Run:  ``python -m seeds.generate``  (uses app.db engine; drops + recreates tables)
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
from sqlalchemy import text

from app.config import settings
from app.db import engine

# ---------------------------------------------------------------- constants
ASOF = date(2026, 6, 30)
SCHOOL_DAYS_PER_YEAR = 150
INSTALMENTS_PER_YEAR = 6
SECTIONS = ["A", "B", "C"]
LEVELS = [6, 7, 8, 9, 10]
YEAR_LABELS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
# current-year headcount per level -> sums to ~550 active students
CURRENT_LEVEL_COUNT = {6: 120, 7: 115, 8: 110, 9: 105, 10: 100}

SUBJECTS = [
    ("EN", "English", "english", 100, 0),
    ("MA", "Marathi", "marathi", 40, 0),
    ("HI", "Hindi", "hindi", 40, 0),
    ("M", "Mathematics", "english", 40, 60),   # MSBSHSE HSC: 40 theory + 60 practical
    ("S", "Science", "english", 60, 40),
    ("SS", "Social Science", "english", 60, 0),
    ("C", "Computer", "english", 60, 40),
    ("IT", "IT & Drawing", "english", 50, 50),
]

# 4 exams/year: two internal (CIA) + pre-board + board; 25% weight each
EXAMS = [
    ("Internal 1", "internal", 25.0),
    ("Internal 2", "internal", 25.0),
    ("Pre-Board", "external", 25.0),
    ("HSC Board", "external", 25.0),
]

FEE_HEADS = [
    ("TUITION", "Tuition Fee", 0),
    ("EXAM", "Exam & Development Fee", 0),
    ("TRANSPORT", "Transport Charge", 0),
    ("ACTIVITY", "Activity & PTA Levy", 18),
]

# archetype -> (attendance base, ability, pay-on-time prob, withdrawal prob)
ARCH = {
    "star":     (0.95, 0.88, 0.98, 0.00),
    "steady":   (0.88, 0.72, 0.85, 0.03),
    "slipping": (0.70, 0.55, 0.55, 0.18),
    "at_risk":  (0.55, 0.40, 0.30, 0.45),
}
ARCH_MIX = [("star", 0.30), ("steady", 0.42), ("slipping", 0.18), ("at_risk", 0.10)]

TUITION_PAISE = {6: 4_200_000, 7: 4_500_000, 8: 4_800_000, 9: 5_200_000, 10: 5_600_000}


def _pick_archetype(rng: np.random.Generator) -> str:
    r = rng.random()
    acc = 0.0
    for name, p in ARCH_MIX:
        acc += p
        if r < acc:
            return name
    return "steady"


def _school_days(start: date, count: int) -> list[date]:
    days: list[date] = []
    d = start
    while len(days) < count:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def _grade(pct: float) -> tuple[str, bool]:
    if pct >= 90: return "O", True
    if pct >= 80: return "A", True
    if pct >= 70: return "B", True
    if pct >= 60: return "C", True
    if pct >= 50: return "D", True
    if pct >= 33: return "E", True
    return "F", False


def _fiscal(d: date) -> int:
    return d.year if d.month >= 4 else d.year - 1


def build(days_per_year: int | None = None, limit_students: int | None = None) -> dict:
    """Seed the engine's database. ``days_per_year`` / ``limit_students`` allow
    a fast mini-seed for the determinism test (same code path, smaller scale)."""
    t0 = time.time()
    import app.models  # noqa: F401  register all tables
    from app.db import Base, SQLModel
    # Close any pooled connections (a leaked Session holds one, which SQLite
    # treats as a lock). On an in-memory DB this also resets to a fresh DB, so
    # drop_all is a no-op and create_all rebuilds everything cleanly.
    engine.dispose()
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    school_days = days_per_year or SCHOOL_DAYS_PER_YEAR
    rng = np.random.default_rng(settings.seed)
    counts: dict[str, int] = {}

    with engine.begin() as conn:
        # ================= Board + academic years =========================
        conn.execute(text(
            "INSERT INTO board (id, code, name) VALUES (1, 'MSBSHSE', "
            "'Maharashtra State Board (HSC)')"))
        for i, lb in enumerate(YEAR_LABELS):
            start = date(2021 + i, 4, 1)
            end = ASOF if lb == "2025-26" else date(2022 + i, 3, 31)
            conn.execute(text(
                "INSERT INTO academic_year (board_id, label, start_date, end_date, asof_date) "
                "VALUES (1, :l, :s, :e, :a)"), {"l": lb, "s": start, "e": end, "a": ASOF})
        yid = {lb: int(r[0]) for lb, r in zip(YEAR_LABELS, conn.execute(
            text("SELECT id FROM academic_year ORDER BY start_date")).all())}
        counts["academic_years"] = len(YEAR_LABELS)

        # ================= Subjects + schemes + teachers ===================
        for code, name, medium, tm, pm in SUBJECTS:
            conn.execute(text(
                "INSERT INTO subject (code, name, medium) VALUES (:c,:n,:m)"),
                {"c": code, "n": name, "m": medium})
        for t in range(40):
            conn.execute(text(
                "INSERT INTO teacher (name, staff_code, subject_ids) "
                "VALUES (:n,:c,'[0]')"), {"n": f"Teacher {t+1:03d}", "c": f"T{t+1:03d}"})
        counts["teachers"] = 40
        counts["subjects"] = len(SUBJECTS)

        # board-accurate assessment schemes (level-10 = MSBSHSE HSC split,
        # e.g. Maths 40 theory + 60 practical; lower levels generic)
        subj_id = {r.code: r.id for r in conn.execute(
            text("SELECT id, code FROM subject")).all()}
        scheme_rows = []
        for code, _n, _m, tm, pm in SUBJECTS:
            for lvl in LEVELS:
                t_max, p_max = (tm, pm) if lvl == 10 else (max(tm, 40), pm)
                scheme_rows.append({"s": subj_id[code], "y": yid["2025-26"],
                                    "l": lvl, "t": t_max, "p": p_max})
        conn.execute(text(
            "INSERT INTO subject_scheme (subject_id, year_id, level, theory_max, "
            "practical_max) VALUES (:s,:y,:l,:t,:p)"), scheme_rows)
        counts["schemes"] = len(scheme_rows)

        # ================= Students + guardians ===========================
        s_id = 0
        students: list[dict] = []
        for lvl in LEVELS:
            for _ in range(CURRENT_LEVEL_COUNT[lvl]):
                s_id += 1
                if limit_students and s_id > limit_students:
                    break
                students.append({
                    "id": s_id, "level": lvl, "arch": _pick_archetype(rng),
                    "aadhaar_masked": f"XXXX-XXXX-{int(rng.integers(1000, 9999))}",
                    "uin": f"MS{2000000 + s_id}",
                    "gender": "M" if rng.random() < 0.52 else "F",
                    # ~15 years old in class 10, ~11 in class 6 (+/- 6 months)
                    "dob": ASOF - timedelta(days=int((lvl + 4) * 365 + rng.integers(-180, 180))),
                    "active": (s_id % 7 != 0),
                })
        stu_rows = [
            {"id": s["id"], "adm": f"ADM{s['id']:05d}", "n": f"Student {s['id']:04d}",
             "uin": s["uin"], "aad": s["aadhaar_masked"], "dob": s["dob"],
             "g": s["gender"], "act": s["active"]} for s in students]
        conn.execute(text(
            "INSERT INTO student (id, admission_no, name, uin_id, aadhaar_masked, "
            "date_of_birth, gender, active, guardian_ids, address) "
            "VALUES (:id,:adm,:n,:uin,:aad,:dob,:g,:act,'[]','')"), stu_rows)
        guard_rows = [
            {"id": s["id"], "n": f"Guardian {s['id']:04d}",
             "p": f"+919{int(rng.integers(0, 100000000))}", "aad": s["aadhaar_masked"]}
            for s in students]
        conn.execute(text(
            "INSERT INTO guardian (id, name, phone, relation, consent_given, aadhaar_masked) "
            "VALUES (:id,:n,:p,'father',TRUE,:aad)"), guard_rows)
        # CAST keeps this portable: Postgres won't do text || int, SQLite rejects ::
        conn.execute(text(
            "UPDATE student SET guardian_ids = (SELECT '['||CAST(g.id AS TEXT)||']' "
            "FROM guardian g WHERE g.id = student.id)"))
        counts["students"] = len(students)

        # ================= Class sections + enrollments + admissions ======
        cs_rows = []
        for lb in YEAR_LABELS:
            for lvl in LEVELS:
                for sec in SECTIONS:
                    cs_rows.append({"y": yid[lb], "l": lvl, "s": sec})
        conn.execute(text(
            "INSERT INTO class_section (year_id, level, section) VALUES (:y,:l,:s)"),
            cs_rows)
        cs = {(r.year_id, r.level, r.section): r.id for r in conn.execute(
            text("SELECT id, year_id, level, section FROM class_section")).all()}

        # each student's level in academic year Y: current_level - (4 - idx(Y))
        idx = {lb: i for i, lb in enumerate(YEAR_LABELS)}
        idx_inv = {v: k for k, v in idx.items()}
        enroll_rows = []
        for s in students:
            for lb in YEAR_LABELS:
                lvl_in_year = s["level"] - (4 - idx[lb])
                if not (6 <= lvl_in_year <= 10):
                    continue  # not yet in school / graduated that year
                withdrew = (lb == "2025-26" and s["arch"] == "at_risk"
                            and s["id"] % 5 == 0)
                enroll_rows.append({
                    "s": s["id"], "y": yid[lb], "lb": lb,
                    "cs": cs[(yid[lb], lvl_in_year, "A")],
                    "st": "withdrew" if withdrew else "active",
                    "wd": date(2026, 5, 15) if withdrew else None,
                })
        conn.execute(text(
            "INSERT INTO enrollment (student_id, year_id, class_section_id, status, "
            "withdrawal_date) VALUES (:s,:y,:cs,:st,:wd)"),
            [{k: v for k, v in r.items() if k != "lb"} for r in enroll_rows])
        # (student, year_label) -> enrollment id, needed for attendance FK
        enr_by: dict[tuple, int] = {}
        for r in conn.execute(text(
            "SELECT e.id, e.student_id, y.label AS lb FROM enrollment e "
            "JOIN academic_year y ON y.id=e.year_id")).all():
            enr_by[(r.student_id, r.lb)] = r.id
        ayears = {v: k for k, v in yid.items()}
        stu_by_id = {s["id"]: s for s in students}
        # admissions snapshot for the current year (funnel + RTE/EWS flags)
        for s in students:
            lb = "2025-26"
            conn.execute(text(
                "INSERT INTO admission (year_id, student_id, stage, rte_ews, admission_date) "
                "VALUES (:y,:s,:st,:rte,:d)"),
                {"y": yid[lb], "s": s["id"],
                 "st": "withdrawn" if (s["arch"] == "at_risk" and s["id"] % 5 == 0)
                        else "enrolled",
                 "rte": s["id"] % 4 == 0,
                 "d": date(2025, 5, 10 + (s["id"] % 20))})
        counts["enrollments"] = len(enroll_rows)

        # ================= Attendance (bulk) ===============================
        att_rows = []
        for er in enroll_rows:
            s = stu_by_id[er["s"]]
            base, _ab, _po, _wd = ARCH[s["arch"]]
            noise = rng.random() * 0.12 - 0.06
            lb = er["lb"]
            start = date(2021 + idx[lb], 4, 1)
            days = _school_days(start, school_days)
            enr = enr_by[(er["s"], lb)]
            for di, d in enumerate(days):
                season = di / len(days)
                dip = 0.25 * season if s["arch"] in ("slipping", "at_risk") else 0.05 * season
                p = min(0.99, max(0.15, base + noise - dip))
                roll = rng.random()
                t = "P" if roll < p else ("L" if roll < p + 0.05 else "A")
                att_rows.append((enr, er["y"], d, t))
        conn.execute(text(
            "INSERT INTO attendance (enrollment_id, year_id, d, type) "
            "VALUES (:e,:y,:d,:t)"),
            [{"e": r[0], "y": r[1], "d": r[2], "t": r[3]} for r in att_rows])
        counts["attendance"] = len(att_rows)

        # ================= Exams + papers + marks (bulk) ==================
        exam_ids: dict[str, int] = {}
        mark_rows: list[dict] = []
        result_rows: list[dict] = []
        subj_id = {r.code: r.id for r in conn.execute(
            text("SELECT id, code FROM subject")).all()}
        paper_ids: list[tuple[int, int, int, int, int]] = []  # (exam, paper, subj, tmax, pmax)

        for lb in YEAR_LABELS:
            ayears = {v: k for k, v in yid.items()}
            start = date(2021 + idx[lb], 4, 1)
            for k, (ename, etype, wgt) in enumerate(EXAMS):
                ws = start + timedelta(days=120 + k * 60)
                we = ws + timedelta(days=10)
                r = conn.execute(text(
                    "INSERT INTO exam (year_id, name, type, window_start, window_end, "
                    "weight_pct) VALUES (:y,:n,:t,:ws,:we,:w) RETURNING id"),
                    {"y": yid[lb], "n": ename, "t": etype, "ws": ws, "we": we, "w": wgt})
                row = r.first()
                eid = int(row[0]) if row is not None else int(r.lastrowid)
                exam_ids[(lb, k)] = eid
                for code, _n, _m, tm, pm in SUBJECTS:
                    pr = conn.execute(text(
                        "INSERT INTO exam_paper (exam_id, subject_id, theory_max, "
                        "practical_max) VALUES (:e,:s,:t,:p) RETURNING id"),
                        {"e": eid, "s": subj_id[code], "t": tm, "p": pm})
                    prow = pr.first()
                    pid = int(prow[0]) if prow is not None else int(pr.lastrowid)
                    paper_ids.append((eid, pid, subj_id[code], tm, pm))

        # marks: one row per (student-in-year, exam, paper)
        stu_by_id = {s["id"]: s for s in students}
        for er in enroll_rows:
            lb = ayears[er["y"]]
            ability = ARCH[stu_by_id[er["s"]]["arch"]][1]
            for k, (_en, _et, _wg) in enumerate(EXAMS):
                eid = exam_ids[(lb, k)]
                for _e, pid, sid, tm, pm in paper_ids:
                    if _e != eid:
                        continue
                    improve = 0.04 * k  # slight progression through the year
                    theory = int(round(tm * min(0.98, max(0.05, ability + rng.random() * 0.2 - 0.1 + improve))))
                    practical = int(round(pm * min(0.95, max(0.1, ability * 0.95 + rng.random() * 0.15)))) if pm else 0
                    total = theory + practical
                    tm_tot = tm + pm
                    grade, passed = _grade(100 * total / tm_tot if tm_tot else 0)
                    mark_rows.append({"p": pid, "s": er["s"], "t": theory,
                                      "pr": practical, "tot": total, "g": grade,
                                      "pf": passed,
                                      "up": datetime(2026, 6, 30, 0, 0, 0, tzinfo=timezone.utc)})
        conn.execute(text(
            "INSERT INTO mark (exam_paper_id, student_id, theory, practical, total, "
            "grade, pass_flag, updated_at) VALUES (:p,:s,:t,:pr,:tot,:g,:pf,:up)"),
            mark_rows)
        counts["marks"] = len(mark_rows)

        # results: roll up per exam per student (SQL aggregate, then insert)
        for (lb, k), eid in exam_ids.items():
            # CASE form (not SUM(bool), not FILTER) so it runs on both
            # SQLite and Postgres
            rows = conn.execute(text(
                "SELECT m.student_id, COALESCE(SUM(m.total),0) AS tot, "
                "COALESCE(SUM(CASE WHEN m.pass_flag THEN 1 ELSE 0 END),0) AS pc, "
                "COUNT(*) AS n FROM mark m "
                "JOIN exam_paper p ON p.id=m.exam_paper_id WHERE p.exam_id=:e "
                "GROUP BY m.student_id"), {"e": eid}).all()
            poss = int(conn.execute(text(
                "SELECT COALESCE(SUM(p.theory_max + p.practical_max),0) "
                "FROM exam_paper p WHERE p.exam_id=:e"), {"e": eid}).scalar())
            for r in rows:
                tot, pc, n = int(r.tot), int(r.pc), int(r.n)
                pct = round(100 * tot / poss, 2) if poss else 0.0
                division = 1 if pct >= 60 else (2 if pct >= 40 else 3)
                grade, _ = _grade(pct)
                result_rows.append({"e": eid, "s": r.student_id, "to": tot, "tp": poss,
                                   "pct": pct, "dv": division, "g": grade,
                                   "pc": pc, "fc": n - pc})
        conn.execute(text(
            "INSERT INTO result (exam_id, student_id, total_obtained, total_possible, "
            "percentage, division, division_rank, overall_grade, pass_count, fail_count) "
            "VALUES (:e,:s,:to,:tp,:pct,:dv,NULL,:g,:pc,:fc)"), result_rows)
        counts["results"] = len(result_rows)

        # ================= Fees: heads, bills, lines, payments ===========
        for code, name, gst in FEE_HEADS:
            conn.execute(text("INSERT INTO fee_head (code, name, gst_rate) VALUES (:c,:n,:g)"),
                         {"c": code, "n": name, "g": gst})
        fid = {r.code: r.id for r in conn.execute(text("SELECT id, code FROM fee_head")).all()}
        gst_rate = {c: g for c, _n, g in FEE_HEADS}

        bill_rows: list[dict] = []
        pay_rows: list[dict] = []
        line_rows: list[dict] = []
        bill_num = 0
        for er in enroll_rows:
            s = stu_by_id[er["s"]]
            arch = s["arch"]
            payontime = ARCH[arch][2]
            lb = ayears[er["y"]]
            start = date(2021 + idx[lb], 4, 1)
            amount_map = {
                "TUITION": TUITION_PAISE[s["level"]] // INSTALMENTS_PER_YEAR,
                "EXAM": 600_000 // INSTALMENTS_PER_YEAR,
                "TRANSPORT": 300_000 // INSTALMENTS_PER_YEAR if s["level"] in (9, 10) else 0,
                "ACTIVITY": 150_000 // INSTALMENTS_PER_YEAR,
            }
            for ins in range(1, INSTALMENTS_PER_YEAR + 1):
                bill_num += 1
                due = start + timedelta(days=(ins - 1) * 62 + 30)
                principal = sum(amount_map.values())
                gst_total = sum(int(amount_map[c] * gst_rate[c] / 100) for c in amount_map)
                total = principal + gst_total
                waived = (arch == "at_risk" and ins == 6 and s["id"] % 3 == 0)
                bill_rows.append({"n": bill_num, "y": yid[lb], "s": er["s"], "i": ins,
                                   "d": due, "w": waived,
                                   "wr": "merit" if waived else None,
                                   "p": principal, "g": gst_total, "t": total})
                for c, amt in amount_map.items():
                    if amt > 0:
                        gline = int(amt * gst_rate[c] / 100)
                        line_rows.append({"b": bill_num, "h": fid[c], "a": amt, "g": gline})
                if waived:
                    continue
                if rng.random() < payontime:
                    mode = ["upi", "cash", "card"][int(rng.integers(0, 3))]
                    paid_at = datetime.combine(due - timedelta(days=int(rng.integers(-10, 5))),
                                        datetime.min.time().replace(tzinfo=None))
                    paid_at = paid_at.replace(tzinfo=timezone.utc)
                    pay_rows.append({"y": yid[lb], "s": er["s"], "b": bill_num,
                                     "at": paid_at, "a": total, "m": mode, "s_": "paid"})
                else:
                    pay_rows.append({"y": yid[lb], "s": er["s"], "b": bill_num,
                                     "at": None, "a": 0, "m": "unpaid", "s_": "open"})
        conn.execute(text(
            "INSERT INTO bill (id, year_id, student_id, installment, due_date, status, "
            "waived, waiver_reason, principal, gst, total, paid) "
            "VALUES (:n,:y,:s,:i,:d,'pending',:w,:wr,:p,:g,:t,0)"), bill_rows)
        conn.execute(text(
            "INSERT INTO bill_line (bill_id, fee_head_id, amount, gst) "
            "VALUES (:b,:h,:a,:g)"), line_rows)

        # settle bills: paid ones get a payment + bill status update
        settled = [p for p in pay_rows if p["s_"] == "paid"]
        p_rows = [
            {"y": p["y"], "s": p["s"], "b": p["b"], "at": p["at"], "a": p["a"], "m": p["m"]}
            for p in settled]
        conn.execute(text(
            "INSERT INTO payment (year_id, student_id, bill_id, paid_at, amount, mode, "
            "receipt_no) VALUES (:y,:s,:b,:at,:a,:m,NULL)"), p_rows)
        conn.execute(text("UPDATE bill SET paid=total, status='paid' "
                          "WHERE status='pending' AND waived=FALSE AND id IN "
                          "(SELECT DISTINCT bill_id FROM payment)"))
        # open bills older than as-of-90d become 'overdue'
        conn.execute(text(
            "UPDATE bill SET status='overdue' WHERE status='pending' AND waived=FALSE "
            "AND due_date < :cutoff"), {"cutoff": ASOF - timedelta(days=90)})
        counts["bills"] = len(bill_rows)
        counts["payments"] = len(p_rows)

        # ================= Receipts (sequential, gap-audited) =============
        pays = conn.execute(text(
            "SELECT p.id, p.student_id, p.year_id, p.amount, p.paid_at FROM payment p "
            "ORDER BY p.paid_at, p.id")).all()
        seq_by_fy: dict[int, int] = {}
        for p in pays:
            paid_dt = p.paid_at if isinstance(p.paid_at, (date, datetime)) \
                else datetime.fromisoformat(str(p.paid_at))
            pfy = _fiscal(paid_dt)
            seq_by_fy[pfy] = seq_by_fy.get(pfy, 0) + 1
            rno = f"FY{pfy}/{seq_by_fy[pfy]:06d}"
            conn.execute(text("UPDATE payment SET receipt_no=:r WHERE id=:i"),
                         {"r": rno, "i": p.id})
            conn.execute(text(
                "INSERT INTO receipt (receipt_no, fiscal_year, year_id, payment_ids, "
                "student_id, issued_at, total, gst_total, line_count) "
                "VALUES (:r,:fy,:y,:pi,:s,:at,:t,0,1)"),
                {"r": rno, "fy": pfy, "y": p.year_id, "pi": json.dumps([int(p.id)]),
                 "s": p.student_id, "at": p.paid_at, "t": p.amount})
        for pfy, n in seq_by_fy.items():
            conn.execute(text(
                "INSERT INTO receipt_sequence (fiscal_year, last_no) VALUES (:f,:n)"),
                {"f": pfy, "n": n})
        counts["receipts"] = len(pays)

        # ================= Demo users =====================================
        from app.security import hash_password
        demo = [
            ("admin", "admin", "admin", "Administrator", None, None, "AD001"),
            ("teach01", "teacher", "teacher", "Ms. Patil", None, None, "T001"),
            ("parent01", "parent", "parent", "Guardian 0001", 1, 1, None),
            ("stud0001", "student", "student", "Student 0001", 1, None, None),
        ]
        for uname, pw, role, name, sid, gid, staff in demo:
            conn.execute(text(
                "INSERT INTO user (username, password_hash, role, full_name, active, "
                "guardian_id, student_id, staff_code) VALUES (:u,:h,:r,:n,TRUE,:g,:s,:st)"),
                {"u": uname, "h": hash_password(pw), "r": role, "n": name,
                 "g": gid, "s": sid, "st": staff})
        counts["users"] = len(demo)

    # keep a create_all-built DB consistent with Alembic so future migrations
    # apply on top instead of re-running the initial schema. ensure_schema opens
    # its own connection from the URL (harmless for in-memory test DBs).
    from app.migrate import ensure_schema
    try:
        ensure_schema(engine)
    except Exception:
        pass  # stamping is best-effort; never block a successful seed

    counts["seconds"] = round(time.time() - t0, 1)
    return counts


def run() -> dict:
    counts = build()
    print(json.dumps(counts, indent=2, default=str))
    return counts


if __name__ == "__main__":
    run()
