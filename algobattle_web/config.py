from __future__ import annotations
import tomli
from pathlib import Path
from base64 import b64decode

ALGORITHM = "HS256"

try:
    with open(Path(__file__).parent / "config.toml", "rb") as f:
        toml_dict = tomli.load(f)
    config = toml_dict["algobattle_web"]
    SECRET_KEY = b64decode(config["secret_key"])
    SQLALCHEMY_DATABASE_URL = config["database_url"]
    ADMIN_EMAIL = config["admin_email"]
except (KeyError, OSError):
    raise SystemExit("Badly formatted or missing config.toml!")