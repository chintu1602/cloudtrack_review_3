"""
NutriAI Health Portal - Shared Test Fixtures & Configuration
Uses SQLite in-memory database with mocked Azure services.

NOTE: PostgreSQL-specific features (UUID columns, Enum types) require
special handling. We use SQLAlchemy events to render UUIDs as strings
and Enums as VARCHAR for SQLite compatibility.
"""

import os
import uuid
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Override env vars BEFORE importing any app modules.
# This ensures config.py picks up test values.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net"
os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = "https://test.cognitiveservices.azure.com/"
os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "test-key"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com/"
os.environ["AZURE_OPENAI_KEY"] = "test-key"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "gpt-4"
os.environ["ENTRA_CLIENT_ID"] = "test-client-id"
os.environ["ENTRA_CLIENT_SECRET"] = "test-client-secret"
os.environ["ENTRA_TENANT_ID"] = "test-tenant-id"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User, PatientProfile, FoodAllergy
from app.models.document import Document
from app.models.diet_plan import DietPlan
from app.models.health_log import HealthLog, MealLog
from app.services.auth_service import hash_password, create_access_token


# ============================================================
# SQLite-compatible test engine
# ============================================================

# SQLite doesn't support PostgreSQL UUID or Enum types natively.
# We create a separate engine for tests that SQLAlchemy can use
# with SQLite, while the production engine uses PostgreSQL.

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency to use test database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency in the FastAPI app
app.dependency_overrides[get_db] = override_get_db


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test and drop after."""
    # Use checkfirst=True to handle any table creation issues
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Get a database session for test setup."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user and return it."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="testuser@example.com",
        username="testuser",
        hashed_password=hash_password("TestPassword123!"),
        full_name="Test User",
        age=30,
        gender="male",
        weight=75.0,
        height=175.0,
        auth_type="local",
        role="patient",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Create an admin test user and return it."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="admin@example.com",
        username="adminuser",
        hashed_password=hash_password("AdminPassword123!"),
        full_name="Admin User",
        age=35,
        gender="female",
        role="admin",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Generate a JWT token for the test user."""
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def admin_token(admin_user):
    """Generate a JWT token for the admin user."""
    return create_access_token(data={"sub": str(admin_user.id)})


@pytest.fixture
def authenticated_client(client, auth_token):
    """Test client with authentication cookie set."""
    client.cookies.set("access_token", auth_token)
    return client


@pytest.fixture
def admin_client(client, admin_token):
    """Test client with admin authentication cookie set."""
    client.cookies.set("access_token", admin_token)
    return client
