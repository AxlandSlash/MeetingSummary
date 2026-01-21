"""数据库连接管理"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from meet_conclusion.config import get_config
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)

# 全局引擎实例
_engine = None


def get_engine():
    """获取数据库引擎"""
    global _engine
    if _engine is None:
        config = get_config()
        db_url = f"sqlite:///{config.db_path}"
        _engine = create_engine(
            db_url,
            echo=config.debug,
            connect_args={"check_same_thread": False}
        )

        # 启用外键约束
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        logger.info(f"数据库引擎初始化完成: {config.db_path}")
    return _engine


def init_db() -> None:
    """初始化数据库，创建所有表"""
    from meet_conclusion.db.models import AudioChunk, Meeting, Note, Transcript

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    logger.info("数据库表创建完成")


def get_session() -> Session:
    """获取数据库会话"""
    engine = get_engine()
    return Session(engine)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """数据库会话上下文管理器

    使用示例:
        with session_scope() as session:
            meeting = Meeting(title="test")
            session.add(meeting)
            session.commit()
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        session.close()
