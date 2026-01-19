import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# Database setup - use in-memory for Azure App Service demo (no persistence issues)
# For production, use Azure SQL or PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./users.db")
# Use check_same_thread=False for SQLite  
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)


# Seed data
def seed_database():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            users = [
                User(name="Alice Johnson", email="alice@example.com"),
                User(name="Bob Smith", email="bob@example.com"),
                User(name="Charlie Brown", email="charlie@example.com"),
                User(name="Diana Prince", email="diana@example.com"),
                User(name="Eve Wilson", email="eve@example.com"),
            ]
            db.add_all(users)
            db.commit()
            print("Database seeded with dummy users")
    except Exception as e:
        # Handle race condition with multiple workers
        db.rollback()
        print(f"Database seeding skipped (may already exist): {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield
    # Shutdown


# FastAPI app
app = FastAPI(
    title="Azure SWA Demo API",
    description="A simple FastAPI backend for Azure App Service demo",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Routes
@app.get("/")
async def root():
    return {"message": "Azure SWA Demo API", "status": "healthy"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/users")
async def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": u.id, "name": u.name, "email": u.email} for u in users]


@app.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return {"error": "User not found"}
    return {"id": user.id, "name": user.name, "email": user.email}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
