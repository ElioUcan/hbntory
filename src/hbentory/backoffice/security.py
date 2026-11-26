import os
from datetime import UTC, datetime, timedelta

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()
jwt_key = os.getenv("JWT_SECRET_KEY")
password_hash = PasswordHash.recommended()
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str) -> str:
    return password_hash.hash(password=password)

def verify_password(plain_pass: str, hashed_pass: str) -> bool:
    return password_hash.verify(plain_pass, hashed_pass)

def _get_secret_key() -> str:
    if jwt_key is None or jwt_key == '':
        raise RuntimeError("JWT SECRET KEY NOT SET")
    return jwt_key

def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {'sub': str(subject), 'exp': expire}

    return jwt.encode(payload, _get_secret_key(), algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
