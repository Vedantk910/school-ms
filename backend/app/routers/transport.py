"""Transport: routes with ordered stops, per-stop charges, student assignments,
monthly revenue by stop. Money is paise internally, *_rs strings for display."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.audit import record
from app.db import get_session
from app.dependencies import require_roles
from app.models import AcademicYear, User
from app.models.transport import Route, RouteStop, TransportAssignment

router = APIRouter(prefix="/transport", tags=["transport"])


def _rs(paise: int) -> str:
    return f"{paise // 100}.{paise % 100:02d}"


class AssignIn(BaseModel):
    student_id: int
    stop_name: str
    monthly_charge_paise: int | None = None  # defaults to the stop's charge


@router.get("/routes")
def list_routes(year_label: str = Query("2025-26"),
                session: Session = Depends(get_session),
                user: User = Depends(require_roles("admin", "teacher"))):
    year = session.exec(select(AcademicYear).where(AcademicYear.label == year_label)).first()
    if year is None:
        raise HTTPException(404, "academic year not found")
    routes = session.exec(select(Route).where(Route.year_id == year.id)).all()
    out = []
    for r in routes:
        stops = session.exec(select(RouteStop).where(RouteStop.route_id == r.id)
                             .order_by(RouteStop.sequence)).all()
        out.append({"id": r.id, "name": r.name, "level": r.level,
                    "direction": r.direction, "stops": [
                        {"sequence": st.sequence, "stop_name": st.stop_name,
                         "charge_rs": _rs(st.charge_paise)} for st in stops]})
    return out


@router.get("/routes/{route_id}")
def route_detail(route_id: int, session: Session = Depends(get_session),
                 user: User = Depends(require_roles("admin", "teacher"))):
    r = session.get(Route, route_id)
    if r is None:
        raise HTTPException(404, "route not found")
    stops = session.exec(select(RouteStop).where(RouteStop.route_id == r.id)
                         .order_by(RouteStop.sequence)).all()
    counts = dict(session.exec(
        select(TransportAssignment.route_stop_id, func.count(TransportAssignment.id))
        .where(TransportAssignment.status == "active")
        .group_by(TransportAssignment.route_stop_id)).all())
    return {"id": r.id, "name": r.name, "level": r.level, "direction": r.direction,
            "stops": [
                {"sequence": st.sequence, "stop_name": st.stop_name,
                 "charge_paise": st.charge_paise, "charge_rs": _rs(st.charge_paise),
                 "assigned_students": counts.get(st.id, 0),
                 "monthly_revenue_paise": st.charge_paise * counts.get(st.id, 0),
                 "monthly_revenue_rs": _rs(st.charge_paise * counts.get(st.id, 0))}
                for st in stops]}


@router.post("/routes/{route_id}/assign")
def assign(route_id: int, body: AssignIn, session: Session = Depends(get_session),
           user: User = Depends(require_roles("admin"))):
    r = session.get(Route, route_id)
    if r is None:
        raise HTTPException(404, "route not found")
    stop = session.exec(select(RouteStop).where(RouteStop.route_id == route_id,
                                                RouteStop.stop_name == body.stop_name)).first()
    if stop is None:
        raise HTTPException(404, f"stop '{body.stop_name}' not on this route")
    charge = body.monthly_charge_paise if body.monthly_charge_paise is not None \
        else stop.charge_paise
    existing = session.exec(select(TransportAssignment).where(
        TransportAssignment.route_stop_id == stop.id,
        TransportAssignment.student_id == body.student_id)).first()
    if existing:
        existing.monthly_charge_paise = charge
        existing.status = "active"
        session.add(existing)
        action = "update"
    else:
        session.add(TransportAssignment(route_stop_id=stop.id,
                                        student_id=body.student_id,
                                        monthly_charge_paise=charge))
        action = "create"
    session.commit()
    record(session, actor=user.username, action=action, resource=f"route#{route_id}",
           detail={"stop": stop.stop_name, "student_id": body.student_id})
    return {"route_id": route_id, "stop": stop.stop_name, "student_id": body.student_id,
            "monthly_charge_paise": charge, "monthly_charge_rs": _rs(charge)}


@router.get("/assignments")
def assignments(stop: str = Query(default=""),
                session: Session = Depends(get_session),
                user: User = Depends(require_roles("admin", "teacher"))):
    q = select(TransportAssignment).where(TransportAssignment.status == "active")
    if stop:
        q = q.join(RouteStop).where(RouteStop.stop_name == stop)
    rows = session.exec(q).all()
    by_stop: dict[str, int] = {}
    for a in rows:
        stop = session.get(RouteStop, a.route_stop_id)
        if stop:
            by_stop[stop.stop_name] = by_stop.get(stop.stop_name, 0) + a.monthly_charge_paise
    return {"active_assignments": len(rows),
            "revenue_by_stop": [
                {"stop_name": k, "monthly_paise": v, "monthly_rs": _rs(v)}
                for k, v in sorted(by_stop.items())]}
