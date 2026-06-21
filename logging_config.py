import logging

logger = logging.getLogger("car_rent")
logger.setLevel(logging.INFO)

handler = logging.FileHandler("logs.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

logger.addHandler(handler)
logger.propagate = False