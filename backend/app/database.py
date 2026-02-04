import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Si existe la variable DATABASE_URL (Nube), úsala. Si no, usa SQLite local.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# Ajuste necesario para Postgres en algunas nubes (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()