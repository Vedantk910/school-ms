"""Deterministic greedy + backtracking weekly-timetable solver.

Pure Python (no numpy). Identical inputs + identical seed => identical plan,
so the demo, tests and any user are always reproducible.

Constraints honoured:
  1. A teacher is at most in one class per (day, slot) globally - passed-in
     cross-section conflicts are treated as booked cells for that teacher.
  2. No more than 2 consecutive periods of the same subject on one day.
  3. The first two subjects in the input list (high priority) each occupy at
     least one morning slot (slot_index <= 4).
  4. Total periods per subject match the requested counts exactly.

When infeasible the solver returns solved=False with a human-readable reason
instead of raising.
"""
from __future__ import annotations

import random
from typing import Any

_DAYS = 5
_MORNING_SLOT = 4  # periods 1-4 are the morning window


def _precheck(slots_per_day: int, subjects: list[dict]) -> str | None:
    demand_total = sum(int(s["periods"]) for s in subjects)
    cells = slots_per_day * _DAYS
    if demand_total > cells:
        return (f"total period demand ({demand_total}) exceeds available cells "
                f"({cells} = {slots_per_day}/day x {_DAYS} days)")
    for s in subjects:
        need = int(s["periods"])
        cap = cells  # one period per cell, all subjects share the grid
        if need > cap:
            return f"subject {s['subject_id']} needs {need} periods but only {cap} exist"
        if s.get("teachers") and need > 0:
            # a subject taught by a single fixed teacher is bounded by that teacher's cells
            if len(s["teachers"]) == 1:
                pass  # teacher capacity is shared across their subjects; checked at search time
    return None


def fill_week(
    class_section_id: int,
    slots_per_day: int,
    subjects: list[dict],
    teachers: list[dict] | None = None,  # kept for API symmetry; per-subject list is used
    conflicts: list[dict] | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """Fill one class-section week deterministically.

    subjects: [{subject_id, periods, teachers: [teacher_ids]}, ...] - input
               order defines priority; the first two are morning-priority.
    conflicts: [{teacher_id, day, slot}, ...] cross-section bookings to avoid.

    Returns {assignments: [(day, slot, subject_id, teacher_id)],
             conflicts_remaining, solved, reason, class_section_id}.
    """
    reason = _precheck(slots_per_day, subjects)
    if reason:
        return {"assignments": [], "conflicts_remaining": 0, "solved": False,
                "reason": reason, "class_section_id": class_section_id}

    rng = random.Random(seed)

    sub_ids: list[int] = [int(s["subject_id"]) for s in subjects]
    sub_left = {int(s["subject_id"]): int(s["periods"]) for s in subjects}
    sub_teachers: dict[int, list[int | None]] = {}
    for s in subjects:
        sid = int(s["subject_id"])
        tlist = [int(t) for t in (s.get("teachers") or [])]
        sub_teachers[sid] = tlist if tlist else [None]
    morning_ids = [sid for sid, n in sub_left.items() if n > 0][:2]
    morning_need = {sid: 1 for sid in morning_ids}

    blocked: set[tuple[int, int, int]] = set()
    for c in conflicts or []:
        blocked.add((int(c["teacher_id"]), int(c["day"]), int(c["slot"])))

    # deterministic per-cell subject order (priority order, seed-shuffled ties
    # only affect *which* valid plan is found first, never determinism)
    order_pool = list(sub_ids)
    rng.shuffle(order_pool)
    base_order = order_pool

    grid: dict[tuple[int, int], tuple[int, int | None]] = {}
    busy: set[tuple[int, int, int]] = set()  # (teacher, day, slot)

    def run_of(day: int, slot: int, subj: int) -> int:
        n, s = 0, slot - 1
        while s >= 1 and grid.get((day, s), (None, None))[0] == subj:
            n += 1
            s -= 1
        return n

    def dfs(day: int, slot: int) -> bool:
        if day > _DAYS:
            return all(n <= 0 for n in sub_left.values()) and \
                   all(m <= 0 for m in morning_need.values())
        if slot > slots_per_day:
            return dfs(day + 1, 1)

        # Try filling this cell with a subject; deterministic candidate order
        for sid in base_order:
            if sub_left[sid] <= 0:
                continue
            if run_of(day, slot, sid) >= 2:
                continue
            for t in sub_teachers[sid]:
                if t is not None and ((t, day, slot) in blocked
                                      or (t, day, slot) in busy):
                    continue
                grid[(day, slot)] = (sid, t)
                if t is not None:
                    busy.add((t, day, slot))
                sub_left[sid] -= 1
                if sid in morning_need and slot <= _MORNING_SLOT:
                    morning_need[sid] -= 1
                if dfs(day, slot + 1):
                    return True
                sub_left[sid] += 1
                if sid in morning_need and slot <= _MORNING_SLOT:
                    morning_need[sid] += 1
                del grid[(day, slot)]
                if t is not None:
                    busy.discard((t, day, slot))
        # Leave the cell empty and move on (demand may be less than cell count)
        grid[(day, slot)] = (None, None)
        if dfs(day, slot + 1):
            return True
        del grid[(day, slot)]
        return False

    if not dfs(1, 1):
        return {"assignments": [], "conflicts_remaining": len(blocked),
                "solved": False,
                "reason": "no schedule satisfies all constraints "
                          "(teacher conflicts, run-length or morning rules)",
                "class_section_id": class_section_id}

    assignments = [(d, s, subj, t) for (d, s), (subj, t) in sorted(grid.items())
                   if subj is not None]
    return {"assignments": assignments, "conflicts_remaining": 0, "solved": True,
            "reason": None, "class_section_id": class_section_id}
