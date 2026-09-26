import os
os.environ["DATABASE_URL"]="sqlite:///./test.db"
os.environ["UPLOAD_DIR"]="./test_uploads"
os.environ["JWT_SECRET"]="test-secret"
os.environ["MODEL_API_URL"]="http://localhost:8001"
os.environ["AVERAGE_BRAIN_HEIGHT_MM"]="150"
import pytest
from fastapi.testclient import TestClient
from app.core.database import Base, engine
from app.main import app
@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
@pytest.fixture
def client():
    with TestClient(app) as c: yield c
@pytest.fixture
def auth(client):
    client.post("/api/auth/signup",json={"name":"Test","email":"test@example.com","password":"password123"})
    token=client.post("/api/auth/login",json={"email":"test@example.com","password":"password123"}).json()["access_token"]
    return {"Authorization":f"Bearer {token}"}
