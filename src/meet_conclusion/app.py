"""应用初始化模块"""

from PySide6.QtWidgets import QApplication

from meet_conclusion.config import get_config
from meet_conclusion.db.database import init_db
from meet_conclusion.utils.logger import setup_logger, get_logger


def run_app() -> int:
    """运行应用"""
    # 初始化配置
    config = get_config()

    # 初始化日志
    setup_logger()
    logger = get_logger(__name__)
    logger.info(f"启动 {config.name} v{config.version}")

    # 初始化数据库
    init_db()

    # 创建Qt应用
    app = QApplication([])
    app.setApplicationName(config.name)
    app.setApplicationVersion(config.version)

    # 创建主窗口
    from meet_conclusion.ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    logger.info("应用启动完成")
    return app.exec()
