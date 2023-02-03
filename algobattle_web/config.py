import tomllib
from pathlib import Path
from base64 import b64decode

from pydantic import validator

from algobattle_web.util import BaseSchema

class Config(BaseSchema):
    algorithm: str = "HS256"
    secret_key: bytes
    database_url: str
    admin_email: str
    storage_path: Path

    @validator("secret_key")
    def parse_b64(self, val) -> bytes:
        return b64decode(val)


try:
    with open(Path(__file__).parent / "config.toml", "rb") as f:
        toml_dict = tomllib.load(f)
    SERVER_CONFIG = Config.parse_obj(toml_dict)
except (KeyError, OSError):
    raise SystemExit("Badly formatted or missing config.toml!")