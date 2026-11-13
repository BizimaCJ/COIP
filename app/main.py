from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping, shape
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .db import get_db, init_db
from .scoring import default_priority, severity_for
from .state_machine import (
    TRANSITIONS,
    InvalidTransition,
    ReasonRequired,
    Status,
    TransitionError,
    allowed_from,
    validate_transition,
)

DESCRIPTION = """
**COIP case engine.** Every detected forest-loss patch becomes a *case*.
A case moves through one lifecycle, and **only the arrows in `GET /transitions` are allowed**.
Every change is logged with who, when and why: that log is the M&E record.

Try it: create a case, then try to jump `detected` to `closed` and watch it get rejected.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="COIP Case Engine", version="0.1.0", description=DESCRIPTION, lifespan=lifespan)


def case_out(case: models.Case, with_geometry: bool = False) -> schemas.CaseOut:
    geometry = None
    if with_geometry and case.geom is not None:
        geometry = mapping(to_shape(case.geom))
    return schemas.CaseOut(
        id=case.id,
        protected_area_id=case.protected_area_id,
        protected_area=case.protected_area.name,
        area_ha=case.area_ha,
        severity=case.severity,
        priority_code=case.priority_code,
        status=case.status,
        detected_at=case.detected_at,
        closed_at=case.closed_at,
        allowed_next=[s.value for s in allowed_from(case.status)],
        geometry=geometry,
    )


def get_case_or_404(db: Session, case_id: int, lock: bool = False) -> models.Case:
    stmt = select(models.Case).where(models.Case.id == case_id)
    if lock:
        stmt = stmt.with_for_update()  # two people can't move the same case at once
    case = db.execute(stmt).scalar_one_or_none()
    if case is None:
        raise HTTPException(404, f"Case {case_id} not found")
    return case


def require_user(db: Session, user_id: int) -> models.AppUser:
    user = db.get(models.AppUser, user_id)
    if user is None:
        raise HTTPException(404, f"User {user_id} not found")
    return user


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get("/transitions", tags=["lifecycle"], summary="The allowed lifecycle arrows")
def list_transitions():
    return [
        {"from": src.value, "to": dst.value, "meaning": meaning}
        for src, targets in TRANSITIONS.items()
        for dst, meaning in targets.items()
    ]


@app.get("/protected-areas", tags=["reference"])
def list_protected_areas(db: Session = Depends(get_db)):
    rows = db.execute(select(models.ProtectedArea).order_by(models.ProtectedArea.id)).scalars()
    return [{"id": r.id, "name": r.name} for r in rows]


@app.get("/users", tags=["reference"])
def list_users(db: Session = Depends(get_db)):
    rows = db.execute(select(models.AppUser).order_by(models.AppUser.id)).scalars()
    return [{"id": r.id, "name": r.name, "role": r.role, "team_id": r.team_id} for r in rows]


@app.post("/cases", response_model=schemas.CaseOut, status_code=201, tags=["cases"])
def create_case(body: schemas.CaseCreate, db: Session = Depends(get_db)):
    if db.get(models.ProtectedArea, body.protected_area_id) is None:
        raise HTTPException(404, f"Protected area {body.protected_area_id} not found")
    require_user(db, body.created_by)

    severity = severity_for(body.area_ha)
    geom = None
    if body.geometry:
        try:
            geom = from_shape(shape(body.geometry), srid=4326)
        except Exception:
            raise HTTPException(422, "geometry is not valid GeoJSON") from None

    case = models.Case(
        protected_area_id=body.protected_area_id,
        geom=geom,
        area_ha=body.area_ha,
        severity=severity,
        priority_code=default_priority(severity),
        status=Status.DETECTED.value,
    )
    case.history.append(
        models.CaseStatusLog(
            from_status=None,
            to_status=Status.DETECTED.value,
            changed_by=body.created_by,
            reason=f"Case created: {body.area_ha} ha, severity {severity}",
        )
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case_out(case, with_geometry=True)


@app.get("/cases", response_model=list[schemas.CaseOut], tags=["cases"])
def list_cases(
    status: str | None = None,
    severity: str | None = None,
    protected_area_id: int | None = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(models.Case).order_by(models.Case.priority_code.desc(), models.Case.id)
    if status:
        stmt = stmt.where(models.Case.status == status)
    if severity:
        stmt = stmt.where(models.Case.severity == severity)
    if protected_area_id:
        stmt = stmt.where(models.Case.protected_area_id == protected_area_id)
    return [case_out(c) for c in db.execute(stmt.limit(limit)).scalars()]


@app.get("/cases/{case_id}", response_model=schemas.CaseOut, tags=["cases"])
def get_case(case_id: int, db: Session = Depends(get_db)):
    return case_out(get_case_or_404(db, case_id), with_geometry=True)


@app.get("/cases/{case_id}/history", response_model=list[schemas.LogEntry], tags=["cases"])
def case_history(case_id: int, db: Session = Depends(get_db)):
    return get_case_or_404(db, case_id).history


@app.post(
    "/cases/{case_id}/transition",
    response_model=schemas.CaseOut,
    tags=["lifecycle"],
    summary="Move a case to a new status (illegal moves are rejected with 409)",
    responses={409: {"description": "Transition not allowed from the current status"}},
)
def transition_case(case_id: int, body: schemas.TransitionRequest, db: Session = Depends(get_db)):
    require_user(db, body.changed_by)
    case = get_case_or_404(db, case_id, lock=True)
    old = case.status
    try:
        new = validate_transition(old, body.to_status, body.reason)
    except InvalidTransition as e:
        raise HTTPException(
            409,
            detail={
                "error": "invalid_transition",
                "message": str(e),
                "current_status": e.current.value,
                "requested_status": e.target.value,
                "allowed_next": [s.value for s in e.allowed],
            },
        ) from None
    except ReasonRequired as e:
        raise HTTPException(422, str(e)) from None
    except TransitionError as e:
        raise HTTPException(422, str(e)) from None

    case.status = new.value
    if new is Status.CLOSED:
        case.closed_at = models.now()
    elif old == Status.CLOSED.value:
        case.closed_at = None  # reopened
    case.history.append(
        models.CaseStatusLog(
            from_status=old, to_status=new.value, changed_by=body.changed_by, reason=body.reason
        )
    )
    db.commit()
    db.refresh(case)
    return case_out(case)
