import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    c = TestClient(app)
    c.session_factory = Session
    yield c
    app.dependency_overrides.clear()


def _auth(client, email):
    client.post("/api/auth/register", json={"full_name": "Test User", "email": email, "password": "Passw0rd123"})
    token = client.post("/api/auth/login", json={"email": email, "password": "Passw0rd123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth(client):
    return _auth(client, "user1@example.com")


@pytest.fixture()
def auth2(client):
    return _auth(client, "user2@example.com")
