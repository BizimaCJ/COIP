"""API tests run against a real PostgreSQL/PostGIS database (never your dev data):
a separate database called coip_test, created automatically."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app import models
from app.config import DATABASE_URL as BASE_URL
from app.db import Base, get_db, init_db
from app.main import app

TEST_URL = make_url(BASE_URL).set(database="coip_test")


@pytest.fixture(scope="session")
def engine():
    admin = create_engine(make_url(BASE_URL).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        if not c.execute(text("SELECT 1 FROM pg_database WHERE datname='coip_test'")).scalar():
            c.execute(text("CREATE DATABASE coip_test"))
    eng = create_engine(TEST_URL)
    init_db(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def client(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        park = models.ProtectedArea(name="Nyungwe")
        team = models.Team(name="Nyungwe Rangers")
        s.add_all([park, team]); s.flush()
        s.add_all([
            models.AppUser(name="Manager", role="manager"),
            models.AppUser(name="Ranger", role="field", team_id=team.id),
        ])
        s.commit()

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
