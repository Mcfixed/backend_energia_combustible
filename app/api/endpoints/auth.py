from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud import crud_user
from app.core import security
from app.schemas import token as token_schema
from app.schemas.token import AccessTokenResponse
from app.api.dependencies import get_current_active_user
from app.models import user as user_model # <--- ¡Importante!
from pydantic import BaseModel
router = APIRouter()

@router.post("/token", response_model=token_schema.Token)
def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    user = crud_user.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Preparamos los datos para los tokens
    token_data = {"sub": user.email}
    
    # Creamos AMBOS tokens
    access_token = security.create_access_token(data=token_data)
    refresh_token = security.create_refresh_token(data=token_data) # <--- ¡NUEVO!
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
@router.post("/token/refresh", response_model=AccessTokenResponse)
def refresh_access_token(
    # Reutilizamos tu dependencia 'get_current_active_user'.
    # El frontend enviará el REFRESH token aquí.
    # Esta dependencia validará si el refresh token es legítimo,
    # no ha expirado, y el usuario existe y está activo.
    current_user: user_model.User = Depends(get_current_active_user)
):
    # Si la dependencia pasa, significa que el refresh token es válido.
    # Simplemente generamos un NUEVO token de acceso.
    new_access_token = security.create_access_token(
        data={"sub": current_user.email}
    )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }    