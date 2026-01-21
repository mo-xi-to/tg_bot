import sys
import logging
from typing import Optional
from logging.handlers import RotatingFileHandler

class LogManager:
    LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    LOG_FILE = "bot.log"

    MAX_BYTES = 5 * 1024 * 1024
    BACKUP_COUNT = 5

    @classmethod
    def setup_logger(cls, name: str = "TimeM_Bot") -> logging.Logger:
        
        """Настраивает и возвращает объект логгера"""

        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        if logger.hasHandlers():
            return logger
        
        formatter = logging.Formatter(fmt=cls.LOG_FORMAT, datefmt=cls.DATE_FORMAT)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            cls.LOG_FILE,
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        for lib_name in ["aiogram", "apscheduler"]:
            lib_logger = logging.getLogger(lib_name)
            lib_logger.addHandler(console_handler)
            lib_logger.addHandler(file_handler)
            lib_logger.propagate = False

        return logger
    
logger = LogManager.setup_logger()
