import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup - supports SQLite (local) or PostgreSQL (production via Neon)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./users.db")
logger.info(f"Database URL scheme: {DATABASE_URL.split('://')[0] if '://' in DATABASE_URL else 'unknown'}")

# Configure connection args based on database type
connect_args = {}
engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL (Neon) configuration with connection pooling
    # Neon free tier can have cold starts of 5-10+ seconds
    engine_kwargs = {
        "poolclass": QueuePool,
        "pool_size": 2,
        "max_overflow": 3,
        "pool_timeout": 60,  # Wait up to 60s for connection (Neon cold start)
        "pool_pre_ping": True,  # Verify connections are alive
        "pool_recycle": 300,  # Recycle connections every 5 min
    }
    # Set connect timeout for Neon cold starts
    connect_args = {"connect_timeout": 60}

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    email = Column(String(255), unique=True, index=True)


# Seed data
def seed_database():
    """Seed database with initial data. Handles cold starts with retry."""
    max_retries = 3
    for attempt in range(max_retries):
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
                logger.info("Database seeded with dummy users")
            else:
                logger.info("Database already has users, skipping seed")
            return  # Success
        except Exception as e:
            # Handle race condition with multiple workers or connection issues
            db.rollback()
            logger.warning(f"Database seeding attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
        finally:
            db.close()
    logger.error("Database seeding failed after all retries")


def init_database():
    """Initialize database tables with retry for cold starts."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting database initialization (attempt {attempt + 1})")
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
            return True
        except Exception as e:
            logger.warning(f"Database init attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
    logger.error("Database initialization failed after all retries")
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")
    if init_database():
        seed_database()
    else:
        logger.error("Failed to initialize database - app may not work correctly")
    yield
    # Shutdown
    logger.info("Application shutting down...")


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
