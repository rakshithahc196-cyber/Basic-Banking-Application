import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.api.deps import get_db
from app.db.base import Base


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(main, "engine", engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app, raise_server_exceptions=False) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def register_user(client):
    def create_user(name="Alex Morgan", email="alex@example.com", password="CorrectHorse12!"):
        registration = client.post(
            "/api/auth/register",
            json={"name": name, "email": email, "password": password},
        )
        assert registration.status_code == 201
        login = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        return {
            "account_number": registration.json()["account_number"],
            "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
            "email": email,
            "password": password,
        }

    return create_user