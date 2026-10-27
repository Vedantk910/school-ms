"""Feature builders for the at-risk and fee-default tasks (decision D4).

No-leakage rule: features for year Y use only data available on 30-Nov-Y
(marks through Internal 1, attendance through November, fees through Q1).
Labels may use the full year Y, because that is the event being predicted.

Computation runs over aggregated SQL pulls in pandas so it stays fast at the
full synthetic scale (≈240k attendance rows). Deterministic given the seed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlmodel import Session

FEATURES = [
    "att_first_half", "att_recent_90", "att_delta", "streak_absent_max",
    "leave_share", "low_subjects", "prev_year_at_risk", "prior_grade_band",
    "rte_ews", "level", "dues_nov", "overdue_days_nov",
    "installments_paid_nov", "prior_default_flag",
]

BAND = {"O": 5, "A": 4, "B": 3, "C": 2, "D": 1, "E": 1, "F": 0}
ASOF = pd.Timestamp("2026-06-30")
# per-year "features available as of 30 Nov" + "label crystallizes by year end"
NOV_REFS = {
    "2021-22": ("2021-04-01", "2021-11-30", "2022-03-31"),
    "2022-23": ("2022-04-01", "2022-11-30", "2023-03-31"),
    "2023-24": ("2023-04-01", "2023-11-30", "2024-03-31"),
    "2024-25": ("2024-04-01", "2024-11-30", "2025-03-31"),
    "2025-26": ("2025-04-01", "2025-11-30", "2026-03-31"),
}


def _pull(session: Session) -> dict[str, pd.DataFrame]:
    def q(sql: str) -> pd.DataFrame:
        # Run the raw SQL on the session's engine and pull into pandas.
        # (fetch_pandas isn't available on the cursor result in this setup.)
        import pandas as _pd
        return _pd.read_sql(text(sql), session.get_bind())

    return {
        "attendance": q(
            "SELECT e.student_id, y.label AS year_label, a.d, a.type "
            "FROM attendance a JOIN enrollment e ON e.id=a.enrollment_id "
            "JOIN academic_year y ON y.id=e.year_id"),
        "marks": q(
            "SELECT m.student_id, y.label AS year_label, m.grade, e.type AS exam_type, "
            "m.total, p.theory_max, p.practical_max "
            "FROM mark m JOIN exam_paper p ON p.id=m.exam_paper_id "
            "JOIN exam e ON e.id=p.exam_id "
            "JOIN academic_year y ON y.id=e.year_id"),
        "enrollment": q(
            "SELECT e.student_id, y.label AS year_label, e.status, cs.level "
            "FROM enrollment e JOIN academic_year y ON y.id=e.year_id "
            "JOIN class_section cs ON cs.id=e.class_section_id"),
        "bills": q(
            "SELECT b.student_id, y.label AS year_label, b.installment, b.due_date, "
            "b.status, b.waived, b.total, b.paid "
            "FROM bill b JOIN academic_year y ON y.id=b.year_id"),
        "admission": q(
            "SELECT a.student_id, a.rte_ews FROM admission a "
            "JOIN academic_year y ON y.id=a.year_id WHERE y.label='2025-26'"),
    }


def build_dataset(session: Session) -> pd.DataFrame:
    """One row per (student, year): all FEATURES + at_risk_label + fee_default_label."""
    data = _pull(session)
    att, marks, enroll = data["attendance"], data["marks"], data["enrollment"]

    # ---- attendance features (as-of 30 Nov per year) --------------------
    att = att.copy()
    att["d"] = pd.to_datetime(att["d"])
    att_long: list[pd.DataFrame] = []
    for lb, (start, nov, _ye) in NOV_REFS.items():
        sub = att[att.year_label == lb]
        fh = sub[(sub.d >= start) & (sub.d <= nov)]
        recent = sub[(sub.d >= (pd.Timestamp(nov) - pd.Timedelta(days=90))) & (sub.d <= nov)]

        first = fh.groupby("student_id")["type"].apply(lambda s: (s == "P").mean())
        recent_m = recent.groupby("student_id")["type"].apply(lambda s: (s == "P").mean())
        leave = sub[sub.d <= nov].groupby("student_id")["type"].apply(
            lambda s: (s == "L").mean())

        out = pd.concat({"att_first_half": first, "att_recent_90": recent_m,
                         "leave_share": leave}, axis=1).fillna(0.0)
        out["att_delta"] = out["att_first_half"] - out["att_recent_90"]
        out["year_label"] = lb
        out.index.name = "student_id"
        out = out.reset_index()
        att_long.append(out)

    att_feat = pd.concat(att_long, ignore_index=True)

    # max consecutive-absent streak within the as-of window (per student-year)
    streak_parts = []
    for lb, (_s, nov, _ye) in NOV_REFS.items():
        sub = att[(att.year_label == lb) & (att.type == "A") &
                  (att.d <= pd.Timestamp(nov))].sort_values(["student_id", "d"])
        streak_parts.append(_max_absent_streak(sub))
    att_feat = att_feat.merge(pd.concat(streak_parts, ignore_index=True),
                              on=["student_id", "year_label"], how="left")
    att_feat["streak_absent_max"] = att_feat["streak_absent_max"].fillna(0).astype(int)

    df = att_feat

    # ---- exam features: low-scoring subject count at Internal 1 ---------
    int1 = marks[marks.exam_type == "internal"].copy()
    int1["pct"] = 100 * int1.total / (int1.theory_max + int1.practical_max)
    low = int1[int1.pct < 45].groupby(["student_id", "year_label"]).size()
    df = df.merge(low.rename("low_subjects").reset_index(),
                  on=["student_id", "year_label"], how="left")
    df["low_subjects"] = df["low_subjects"].fillna(0).astype(int)

    years = list(NOV_REFS.keys())  # ["2021-22", ..., "2025-26"] in order

    def _prior_year(value_col: str, default: float) -> pd.DataFrame:
        """Pivot student x year, shift right by one column so cell (s, Y) holds
        the previous year's value. Returns [student_id, year_label, value_col_prior]."""
        m = df.pivot_table(index="student_id", columns="year_label",
                           values=value_col, aggfunc="max")
        m = m.reindex(columns=years).reset_index()      # student_id back to a column
        shifted = m.set_index("student_id").shift(1, axis=1).fillna(default).reset_index()
        return shifted.melt(id_vars="student_id", var_name="year_label",
                            value_name=f"{value_col}_prior")

    # ---- full-year attendance % (label input) + prior-year at-risk flag
    att_pct = att.groupby(["student_id", "year_label"]).apply(
        lambda g: (g.type == "P").mean(), include_groups=False).rename("att_pct_full")
    df = df.merge(att_pct.reset_index(), on=["student_id", "year_label"], how="left")
    df["att_pct_full"] = df["att_pct_full"].fillna(0.0)
    df["__att_flag__"] = (df["att_pct_full"] < 0.70).astype(int)
    df = df.merge(_prior_year("__att_flag__", 0).rename(
        columns={"__att_flag___prior": "prev_year_at_risk"}),
        on=["student_id", "year_label"], how="left")
    df["prev_year_at_risk"] = df["prev_year_at_risk"].fillna(0).astype(int)

    # ---- prior-year grade band (from that year's mean band) -----------
    marks["band"] = marks.grade.map(BAND)
    band = marks.groupby(["student_id", "year_label"])["band"].mean()
    df = df.merge(band.reset_index().rename(columns={"band": "band_cur"}),
                  on=["student_id", "year_label"], how="left")
    df["band_cur"] = df["band_cur"].fillna(2)
    df = df.merge(_prior_year("band_cur", 2).rename(
        columns={"band_cur_prior": "prior_grade_band"}),
        on=["student_id", "year_label"], how="left")
    df["prior_grade_band"] = df["prior_grade_band"].astype(int).clip(0, 5)

    # ---- student attributes ---------------------------------------------
    if not data["admission"].empty:
        df = df.merge(data["admission"].drop_duplicates("student_id"),
                      on="student_id", how="left")
    df["rte_ews"] = df.get("rte_ews", pd.Series(0, index=df.index)).fillna(0).astype(int)
    lvl = enroll.drop_duplicates(["student_id", "year_label"]).set_index(
        ["student_id", "year_label"])["level"]
    df["level"] = df.set_index(["student_id", "year_label"]).index.map(
        lambda t: lvl.get(t, 6)).astype(int)

    # ---- fees features (as-of 30 Nov of each year, no leakage) ----------
    b = data["bills"].copy()
    b["due_date"] = pd.to_datetime(b["due_date"])
    nov_by_year = pd.Series({lb: pd.Timestamp(v[1]) for lb, v in NOV_REFS.items()})
    ye_by_year = pd.Series({lb: pd.Timestamp(v[2]) for lb, v in NOV_REFS.items()})
    b["nov_cut"] = b.year_label.map(nov_by_year)
    b["ye"] = b.year_label.map(ye_by_year)
    b["open"] = b.total - b.paid
    b["open_at_nov"] = np.where((b.due_date < b.nov_cut) & ~b.waived, b.open, 0)
    b["overdue_at_nov"] = np.where(
        (b.due_date < b.nov_cut) & ~b.waived, (b.nov_cut - b.due_date).dt.days, 0)
    b["paid_by_nov"] = (b.due_date < b.nov_cut) & (b.status == "paid")
    # within-year default: a non-waived bill still open >90 days past its due
    b["default_in_year"] = (b.open > 0) & ~b.waived & ((b.ye - b.due_date).dt.days > 90)
    agg = b.groupby(["student_id", "year_label"]).agg(
        dues_nov=("open_at_nov", "sum"),
        overdue_days_nov=("overdue_at_nov", "max"),
        installments_paid_nov=("paid_by_nov", "sum"),
        default_in_year=("default_in_year", "max")).reset_index()
    df = df.merge(agg, on=["student_id", "year_label"], how="left")
    for c in ["dues_nov", "overdue_days_nov", "installments_paid_nov", "default_in_year"]:
        df[c] = df[c].fillna(0)
    df["dues_nov"] = (df["dues_nov"] / 100000).round(2)  # paise -> 0.01k units
    df["default_in_year"] = df["default_in_year"].astype(int)
    # prior-year default flag (leak-safe: strictly years before Y)
    df = df.merge(_prior_year("default_in_year", 0).rename(
        columns={"default_in_year_prior": "prior_default_flag"}),
        on=["student_id", "year_label"], how="left")
    df["prior_default_flag"] = df["prior_default_flag"].fillna(0).astype(int)

    # ---- labels (full-year Y, as-of year end) ---------------------------
    withdrew = enroll[enroll.status == "withdrew"].drop_duplicates(
        ["student_id", "year_label"]).assign(withdrew_flag=1)
    df = df.merge(withdrew[["student_id", "year_label", "withdrew_flag"]],
                  on=["student_id", "year_label"], how="left")
    df["withdrew_flag"] = df["withdrew_flag"].fillna(0).astype(int)

    df["at_risk_label"] = ((df.withdrew_flag == 1) |
                           (df.att_pct_full < 0.70) |
                           (df.low_subjects >= 3)).astype(int)
    df["fee_default_label"] = df["default_in_year"]

    drop_cols = ["att_pct_full", "_att_prior", "band_cur", "default_in_year",
                 "withdrew_flag"]
    return df.drop(columns=[c for c in drop_cols if c in df.columns])


def _max_absent_streak(sub: pd.DataFrame) -> pd.DataFrame:
    """Longest run of consecutive-calendar absent days, per student-year."""
    def streak(d: pd.Series) -> int:
        d = d.reset_index(drop=True)
        if d.empty:
            return 0
        breaks = d.diff().dt.days > 1
        run, best = 0, 0
        for b in breaks:
            if b:
                best, run = max(best, run + 1), 0
            else:
                run += 1
        return int(best)
    # carry year_label so callers can merge back on (student_id, year_label)
    return sub.groupby(["student_id", "year_label"])["d"].apply(streak,
                                                                 include_groups=False).reset_index(
        name="streak_absent_max")


def split_temporal(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train 2021-22..2024-25, evaluate 2025-26 (decision D4)."""
    train = df[df.year_label.isin(["2021-22", "2022-23", "2023-24", "2024-25"])]
    ev = df[df.year_label == "2025-26"]
    return train, ev
