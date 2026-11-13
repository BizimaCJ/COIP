"""Demo data: 4 pilot parks, 2 teams, 3 users, 5 cases.  Run: python -m app.seed"""
from sqlalchemy import select

from . import models
from .db import SessionLocal, init_db
from .scoring import default_priority, severity_for
from .state_machine import Status

PARKS = ["Nyungwe", "Akagera", "Volcans", "Gishwati-Mukura"]
CASES = [  # (park, area_ha)
    ("Nyungwe", 14.2),  # the example from the brief
    ("Nyungwe", 6.1),
    ("Nyungwe", 0.8),
    ("Gishwati-Mukura", 2.4),
    ("Volcans", 22.5),
]


def seed():
    init_db()
    with SessionLocal() as db:
        if db.execute(select(models.Team)).first():
            print("Already seeded, nothing to do.")
            return
        parks = {n: models.ProtectedArea(name=n) for n in PARKS}
        teams = [models.Team(name="Nyungwe Rangers"), models.Team(name="Volcans Monitors")]
        db.add_all([*parks.values(), *teams])
        db.flush()
        users = [
            models.AppUser(name="Amina (Programme Manager)", role="manager"),
            models.AppUser(name="Jean (Ranger)", role="field", team_id=teams[0].id),
            models.AppUser(name="Chantal (GIS Analyst)", role="analyst"),
        ]
        db.add_all(users)
        db.flush()
        for park, ha in CASES:
            sev = severity_for(ha)
            case = models.Case(
                protected_area_id=parks[park].id, area_ha=ha, severity=sev,
                priority_code=default_priority(sev), status=Status.DETECTED.value,
            )
            case.history.append(models.CaseStatusLog(
                from_status=None, to_status="detected", changed_by=users[2].id,
                reason=f"Case created: {ha} ha, severity {sev}"))
            db.add(case)
        db.commit()
        print(f"Seeded {len(PARKS)} parks, {len(teams)} teams, {len(users)} users, {len(CASES)} cases.")


if __name__ == "__main__":
    seed()
