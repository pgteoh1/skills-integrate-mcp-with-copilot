"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Literal
import os
from pathlib import Path
import hashlib
import hmac
import secrets

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: Literal["student", "club_admin", "federation_admin"] = "student"


class LoginRequest(BaseModel):
    username: str
    password: str


def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, stored_digest = stored.split("$", 1)
    computed = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(computed, stored_digest)


# In-memory users and sessions for demo purposes.
users = {
    "student1": {
        "email": "student1@mergington.edu",
        "password_hash": hash_password("student123"),
        "role": "student",
    },
    "clubadmin": {
        "email": "clubadmin@mergington.edu",
        "password_hash": hash_password("clubadmin123"),
        "role": "club_admin",
    },
    "federation": {
        "email": "federation@mergington.edu",
        "password_hash": hash_password("federation123"),
        "role": "federation_admin",
    },
}

# Token -> username mapping
sessions = {}


def parse_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return token


def get_current_user(authorization: str | None = Header(default=None)):
    token = parse_bearer_token(authorization)
    username = sessions.get(token)
    if not username or username not in users:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = users[username]
    return {
        "username": username,
        "email": user["email"],
        "role": user["role"],
    }


def is_admin(user_role: str) -> bool:
    return user_role in {"club_admin", "federation_admin"}


@app.post("/auth/register")
def register(payload: RegisterRequest):
    username = payload.username.strip().lower()
    email = payload.email.strip().lower()

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    if username in users:
        raise HTTPException(status_code=409, detail="Username already exists")
    if any(user["email"] == email for user in users.values()):
        raise HTTPException(status_code=409, detail="Email is already registered")

    users[username] = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
    }

    return {
        "message": "Registration successful",
        "user": {
            "username": username,
            "email": email,
            "role": payload.role,
        },
    }


@app.post("/auth/login")
def login(payload: LoginRequest):
    username = payload.username.strip().lower()
    user = users.get(username)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    sessions[token] = username

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": username,
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.post("/auth/logout")
def logout(
    current_user=Depends(get_current_user),
    authorization: str | None = Header(default=None),
):
    token = parse_bearer_token(authorization)
    sessions.pop(token, None)
    return {"message": f"Logged out {current_user['username']}"}


@app.get("/auth/me")
def me(current_user=Depends(get_current_user)):
    return current_user


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    current_user=Depends(get_current_user),
):
    """Sign up a student for an activity"""
    normalized_email = email.strip().lower()

    if current_user["role"] == "student" and normalized_email != current_user["email"]:
        raise HTTPException(
            status_code=403,
            detail="Students can only sign up their own account",
        )

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is at full capacity")

    # Validate student is not already signed up
    if normalized_email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(normalized_email)
    return {"message": f"Signed up {normalized_email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    current_user=Depends(get_current_user),
):
    """Unregister a student from an activity"""
    normalized_email = email.strip().lower()

    if not is_admin(current_user["role"]) and normalized_email != current_user["email"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins can unregister other students",
        )

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if normalized_email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(normalized_email)
    return {"message": f"Unregistered {normalized_email} from {activity_name}"}
