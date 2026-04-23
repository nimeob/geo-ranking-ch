"""API-Routen für Authentifizierung und Autorisierung."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from ..dependencies import verify_api_key, limiter
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# --- Konfiguration ---
SECRET_KEY = settings.api_key_header or "default-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Passwort-Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2-Schema
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# --- Modelle ---
class Token(BaseModel):
    """Token-Response-Modell."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    """Daten im Token."""
    username: Optional[str] = None

class User(BaseModel):
    """Benutzermodell."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    """Benutzer in der Datenbank."""
    hashed_password: str

# --- Helferfunktionen ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Überprüft ein Passwort."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Erzeugt einen Passwort-Hash."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Erzeugt ein JWT-Access-Token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Routen ---
@router.post(
    "/token",
    response_model=Token,
    summary="Token für OAuth2-Passwort-Flow abrufen",
    description="Erzeugt ein Access-Token für einen Benutzer.",
    responses={
        200: {"description": "Token erfolgreich erstellt"},
        400: {"description": "Ungültige Anmeldedaten"},
        401: {"description": "Falsches Passwort"},
    },
)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    """Erzeugt ein Access-Token für einen Benutzer."""
    # Platzhalter: Echte Implementierung würde Benutzer aus der DB laden
    user_dict = {
        "username": form_data.username,
        "hashed_password": get_password_hash("fakehashedsecret"),
        "disabled": False,
    }
    
    user = UserInDB(**user_dict)
    
    if not user or user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benutzer nicht gefunden oder deaktiviert",
        )
    
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falsches Passwort",
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )

@router.get(
    "/me",
    response_model=User,
    summary="Aktuellen Benutzer abrufen",
    description="Gibt die Informationen des aktuell angemeldeten Benutzers zurück.",
    responses={
        200: {"description": "Benutzerinformationen"},
        401: {"description": "Nicht autorisiert"},
    },
)
@limiter.limit("10/minute")
async def read_users_me(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> User:
    """Gibt die Informationen des aktuellen Benutzers zurück."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # Platzhalter: Echte Implementierung würde Benutzer aus der DB laden
    user_dict = {
        "username": token_data.username,
        "email": f"{token_data.username}@example.com",
        "full_name": f"{token_data.username.capitalize()} User",
        "disabled": False,
    }
    
    return User(**user_dict)