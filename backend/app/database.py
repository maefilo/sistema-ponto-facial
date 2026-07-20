from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import config


def get_engine():
    connect_args = {}
    if config.CA_PATH:
        connect_args = {
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
            "ssl_ca": config.CA_PATH,
        }

    return create_engine(
        URL.create(
            drivername="mysql+pymysql",
            username=config.TIDB_USER,
            password=config.TIDB_PASSWORD,
            host=config.TIDB_HOST,
            port=config.TIDB_PORT,
            database=config.TIDB_DB_NAME,
        ),
        connect_args=connect_args,
        pool_recycle=300,
        pool_pre_ping=True,
    )


engine = get_engine()
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
