import logging
import sys

HOST = ""
PORT = 50000
READ_BUFFER = 100000
MESSAGE_MAX_LEN = 20480
READ_TIMEOUT = 15 * 60
ENCODING_TYPE = "utf_8"
LOGGING_LEVEL = logging.DEBUG
LOGGING_NAME = "network_testing_tool"

main_logger = logging.getLogger(LOGGING_NAME)


def set_up_logger():
    logger = logging.getLogger(LOGGING_NAME)
    logger.setLevel(LOGGING_LEVEL)

    fh = logging.FileHandler(f"{LOGGING_NAME}.log")
    fh.setLevel(LOGGING_LEVEL)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(LOGGING_LEVEL)

    formatter = logging.Formatter(fmt="%(asctime)s : %(levelname)s %(message)s", datefmt="%H:%M:%S %d.%m.%Y", )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
