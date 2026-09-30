import os
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Header
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models

app = FastAPI(title="Users Service")
engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(bind=engine)
JWT_SECRET = os.environ["JWT_SECRET"]


@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(engine)


def hashpw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify(p, h):
    return bcrypt.checkpw(p.encode(), h.encode())


@app.post("/register")
def register(body: dict):
    db = Session()
    if db.query(models.User).filter_by(email=body["email"]).first():
        raise HTTPException(400, "Email already registered")
    user = models.User(
        email=body["email"],
        password_hash=hashpw(body["password"]),
        name=body.get("name", ""),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "name": user.name}


@app.post("/login")
def login(body: dict):
    db = Session()
    user = db.query(models.User).filter_by(email=body["email"]).first()
    if not user or not verify(body["password"], user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.utcnow() + timedelta(days=7)},
        JWT_SECRET,
        algorithm="HS256",
    )
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }


@app.get("/me")
def me(x_user_id: str = Header(None)):
    if not x_user_id:
        raise HTTPException(401)
    db = Session()
    user = db.query(models.User).get(int(x_user_id))
    if not user:
        raise HTTPException(404)
    return {"id": user.id, "email": user.email, "name": user.name}
