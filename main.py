from contextlib import asynccontextmanager
from datetime import date, datetime
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./taskboard.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase): pass

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    memberships: Mapped[list["Membership"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    assigned_tasks: Mapped[list["Task"]] = relationship(back_populates="assignee")

class Membership(Base):
    __tablename__ = "memberships"
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    project: Mapped[Project] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="todo")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project: Mapped[Project] = relationship(back_populates="tasks")
    assignee: Mapped[User | None] = relationship(back_populates="assigned_tasks")

Status = Literal["todo", "in_progress", "done"]
Priority = Literal["low", "medium", "high"]
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
class MemberCreate(UserCreate): role: Literal["owner", "member"] = "member"
class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=160); description: str = ""; priority: Priority = "medium"; status: Status = "todo"; due_date: date | None = None; assignee_id: int | None = None
class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160); description: str | None = None; priority: Priority | None = None; status: Status | None = None; due_date: date | None = None; assignee_id: int | None = None

def get_db():
    with SessionLocal() as session: yield session
def task_view(task: Task):
    return {"id": task.id, "project_id": task.project_id, "title": task.title, "description": task.description, "priority": task.priority, "status": task.status, "due_date": task.due_date, "assignee_id": task.assignee_id, "assignee": {"id": task.assignee.id, "name": task.assignee.name, "email": task.assignee.email} if task.assignee else None}
def require_project(project_id: int, db: Session):
    project = db.get(Project, project_id)
    if not project: raise HTTPException(404, "Project not found")
    return project
def validate_assignee(project_id: int, assignee_id: int | None, db: Session):
    if assignee_id is not None and not db.get(Membership, {"project_id": project_id, "user_id": assignee_id}): raise HTTPException(422, "Assignee must belong to this project")
def seed(db: Session):
    if db.scalar(select(func.count(Project.id))) > 0: return
    project = Project(name="Product launch")
    ava, leo, mia = User(name="Ava Patel", email="ava@example.com"), User(name="Leo Chen", email="leo@example.com"), User(name="Mia Johnson", email="mia@example.com")
    project.memberships = [Membership(user=ava, role="owner"), Membership(user=leo), Membership(user=mia)]
    project.tasks = [Task(title="Define launch goals", description="Align success metrics with the team.", priority="high", due_date=date.today(), assignee=ava), Task(title="Prepare landing page", description="Write the first responsive draft.", status="in_progress", due_date=date.today(), assignee=leo), Task(title="Research competitor messaging", priority="low", status="done", assignee=mia)]
    db.add(project); db.commit()
@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db: seed(db)
    yield

app = FastAPI(title="FlowBoard API", lifespan=lifespan)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
@app.get("/")
def index(): return FileResponse(STATIC_DIR / "index.html")
@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)): return [{"id": p.id, "name": p.name} for p in db.scalars(select(Project).order_by(Project.id))]
@app.get("/api/projects/{project_id}/board")
def board(project_id: int, db: Session = Depends(get_db)):
    project = require_project(project_id, db); tasks = list(db.scalars(select(Task).where(Task.project_id == project_id).order_by(Task.created_at.desc())))
    members = []
    for membership in project.memberships:
        count = db.scalar(select(func.count(Task.id)).where(Task.project_id == project_id, Task.assignee_id == membership.user_id, Task.status == "in_progress")) or 0
        members.append({"id": membership.user.id, "name": membership.user.name, "email": membership.user.email, "role": membership.role, "in_progress_count": count, "overloaded": count > 5})
    return {"project": {"id": project.id, "name": project.name}, "tasks": [task_view(t) for t in tasks], "members": members}
@app.post("/api/projects/{project_id}/tasks", status_code=201)
def create_task(project_id: int, data: TaskInput, db: Session = Depends(get_db)):
    require_project(project_id, db); validate_assignee(project_id, data.assignee_id, db); task = Task(project_id=project_id, **data.model_dump()); db.add(task); db.commit(); db.refresh(task); return task_view(task)
@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task: raise HTTPException(404, "Task not found")
    changes = data.model_dump(exclude_unset=True)
    if "assignee_id" in changes: validate_assignee(task.project_id, changes["assignee_id"], db)
    for key, value in changes.items(): setattr(task, key, value)
    db.commit(); db.refresh(task); return task_view(task)
@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task: raise HTTPException(404, "Task not found")
    db.delete(task); db.commit()
@app.post("/api/projects/{project_id}/members", status_code=201)
def add_member(project_id: int, data: MemberCreate, db: Session = Depends(get_db)):
    require_project(project_id, db); user = db.scalar(select(User).where(User.email == data.email))
    if not user: user = User(name=data.name, email=data.email); db.add(user); db.flush()
    if db.get(Membership, {"project_id": project_id, "user_id": user.id}): raise HTTPException(409, "This user is already a project member")
    db.add(Membership(project_id=project_id, user_id=user.id, role=data.role)); db.commit(); return {"id": user.id, "name": user.name, "email": user.email, "role": data.role}
