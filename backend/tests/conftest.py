import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.limiter import limiter

# Disable rate limiting for tests
limiter.enabled = False

from sqlalchemy.pool import StaticPool

# Use an in-memory SQLite database for test suites with a StaticPool to keep the DB alive
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    # Create tables once per test session
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables once at the end of the test session
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    from backend.app.routes.challenges import seed_challenges
    seed_challenges(session)
    
    yield session
    
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    # Dependency override to use the testing session
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client):
    """
    Reusable pytest fixture that registers a test user, logs in,
    and yields the Authorization header dict ready for use in any test.

    Usage in a test:
        def test_something(client, auth_headers):
            response = client.get("/api/...", headers=auth_headers)

    A unique username is generated per invocation so parallel parametrize
    calls don't collide on the unique-username DB constraint.
    """
    username = "fixture_user"
    email = f"{username}@example.com"
    password = "password123"

    client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    login_resp = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    token = login_resp.json()["access_token"]
    yield {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def make_auth_headers(client):
    """
    Factory fixture that registers and logs in a user with a given username,
    returning the Authorization header dict.
    """
    def _make(username: str):
        email = f"{username}@example.com"
        password = "password123"
        client.post(
            "/api/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        login_resp = client.post(
            "/api/auth/login",
            data={"username": username, "password": password},
        )
        token = login_resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return _make

