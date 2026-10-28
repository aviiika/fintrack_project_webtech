import logging, sys
from app.config import settings
def configure_logging():
    lvl = getattr(logging, settings.log_level.upper(), logging.INFO)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))
    r = logging.getLogger(); r.setLevel(lvl); r.handlers.clear(); r.addHandler(h)
def get_logger(name): return logging.getLogger(name)
