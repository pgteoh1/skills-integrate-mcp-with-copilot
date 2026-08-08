from uuid import uuid4

from fastapi.testclient import TestClient

from src.app import app


client = TestClient(app)


def unique_username(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}@mergington.edu"


def register_user(username: str, email: str, password: str, role: str = "student"):
    return client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "role": role,
        },
    )


def login_user(username: str, password: str):
    return client.post(
        "/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )


def test_register_login_logout_flow():
    username = unique_username("student")
    password = "securepass123"
    email = unique_email("student")

    register_response = register_user(username, email, password, "student")
    assert register_response.status_code == 200

    login_response = login_user(username, password)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == username

    logout_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    after_logout_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after_logout_response.status_code == 401


def test_login_failure_with_wrong_password():
    username = unique_username("student")
    email = unique_email("student")

    register_response = register_user(username, email, "correctpass123", "student")
    assert register_response.status_code == 200

    failed_login = login_user(username, "wrongpass")
    assert failed_login.status_code == 401


def test_protected_endpoint_rejects_unauthenticated_requests():
    response = client.post(
        "/activities/Chess%20Club/signup?email=guest@mergington.edu",
    )
    assert response.status_code == 401


def test_student_cannot_modify_other_student_registration():
    username = unique_username("student")
    password = "studentpass123"
    email = unique_email("student")
    other_email = unique_email("other")

    register_response = register_user(username, email, password, "student")
    assert register_response.status_code == 200

    login_response = login_user(username, password)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    signup_response = client.post(
        f"/activities/Chess%20Club/signup?email={other_email}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert signup_response.status_code == 403


def test_admin_can_register_other_students_to_activity():
    admin_username = unique_username("admin")
    admin_password = "adminpass123"
    admin_email = unique_email("admin")
    target_email = unique_email("target")

    register_response = register_user(
        admin_username,
        admin_email,
        admin_password,
        "club_admin",
    )
    assert register_response.status_code == 200

    login_response = login_user(admin_username, admin_password)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    signup_response = client.post(
        f"/activities/Chess%20Club/signup?email={target_email}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert signup_response.status_code == 200
