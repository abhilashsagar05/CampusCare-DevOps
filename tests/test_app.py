import pytest
from app import create_app, db


@pytest.fixture()
def client(tmp_path):
    database_file = tmp_path / "test.db"
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_file}",
    })
    with app.test_client() as client:
        yield client


def report_issue(client, title="Broken fan"):
    return client.post("/issues", data={
        "title": title,
        "description": "Fan is not working in the classroom.",
        "location": "Block A, Room 101",
        "category": "Electrical",
        "priority": "High",
        "reporter": "Test Student",
    }, follow_redirects=True)


def sign_in(client, username, password):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"CampusCare" in response.data
    assert b"Staff sign in" in response.data


def test_create_issue_and_api(client):
    response = report_issue(client)
    assert response.status_code == 200
    assert b"reported" in response.data
    data = client.get("/api/issues").get_json()
    assert len(data) == 1
    assert data[0]["title"] == "Broken fan"
    assert data[0]["status"] == "Pending"
    assert data[0]["assigned_technician"] is None


def test_admin_can_assign_and_technician_can_resolve(client):
    report_issue(client)
    sign_in(client, "admin", "AdminDemo123!")
    admin_page = client.get("/admin")
    assert admin_page.status_code == 200
    assert b"Assign technician" in admin_page.data
    with client.application.app_context():
        technician = client.application.User.query.filter_by(username="tech1").first()
        technician_id = technician.id
    response = client.post("/admin/issues/1/assign", data={"technician_id": str(technician_id)}, follow_redirects=True)
    assert response.status_code == 200
    assert b"assigned to" in response.data
    client.post("/logout")
    sign_in(client, "tech1", "TechDemo123!")
    tech_page = client.get("/technician")
    assert b"Broken fan" in tech_page.data
    response = client.post("/technician/issues/1/status", data={"status": "Resolved"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Resolved" in response.data


def test_technician_cannot_update_an_issue_assigned_to_someone_else(client):
    report_issue(client)
    sign_in(client, "admin", "AdminDemo123!")
    with client.application.app_context():
        tech1 = client.application.User.query.filter_by(username="tech1").first()
        tech2 = client.application.User.query.filter_by(username="tech2").first()
        tech1_id, tech2_id = tech1.id, tech2.id
    client.post("/admin/issues/1/assign", data={"technician_id": str(tech1_id)})
    client.post("/logout")
    sign_in(client, "tech2", "TechDemo456!")
    response = client.post("/technician/issues/1/status", data={"status": "Resolved"}, follow_redirects=True)
    assert b"only update issues assigned to you" in response.data


def test_admin_page_requires_admin_login(client):
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    assert b"Sign in to manage issues" in response.data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_invalid_status_is_rejected(client):
    report_issue(client)
    sign_in(client, "admin", "AdminDemo123!")
    with client.application.app_context():
        technician = client.application.User.query.filter_by(username="tech1").first()
        technician_id = technician.id
    client.post("/admin/issues/1/assign", data={"technician_id": str(technician_id)})
    client.post("/logout")
    sign_in(client, "tech1", "TechDemo123!")
    response = client.post("/technician/issues/1/status", data={"status": "Hacked"}, follow_redirects=True)
    assert b"Choose In Progress or Resolved" in response.data
