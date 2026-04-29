# app/database/db.py

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import Config

engine = create_engine(
    Config.DATABASE_URL,
    pool_size=5,
    pool_pre_ping=True,
    echo=Config.DEBUG,
    connect_args={"sslmode": "require"} if "neon.tech" in Config.DB_HOST else {},
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


def get_session():
    """
    Returns a fresh database session.

    Always use this pattern:
        session = get_session()
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    """
    return SessionLocal()


def get_db():
    """
    Generator version — automatically closes session when done.

    Usage:
        with get_db() as session:
            results = session.query(Transaction).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all_tables():
    """
    Creates all tables defined in models.py.
    Safe to run multiple times — skips tables that already exist.
    """
    from app.database import models  # noqa
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created successfully")


def drop_all_tables():
    """
    DANGER: Deletes ALL tables and all data.
    Only use during development to start fresh.
    """
    from app.database import models  # noqa
    confirm = input("This deletes ALL data. Type 'yes' to confirm: ")
    if confirm.lower() == "yes":
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped.")
    else:
        print("Cancelled.")


def test_connection():
    """
    Quick health check — confirms PostgreSQL is reachable.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✓ Connected to PostgreSQL")
            print(f"  Version: {version}")
            return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("  → Check .env file: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
        return False