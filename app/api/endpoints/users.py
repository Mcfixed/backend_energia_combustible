from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud import crud_user
from app.schemas import user as user_schema, company as company_schema
from app.models import user as user_model
from app.api.dependencies import get_current_active_user

from app.models import association
from app.models import company
from app.schemas.user import UserRoleInCompany
from typing import List


router = APIRouter()

@router.post("/users", response_model=user_schema.User, status_code=status.HTTP_201_CREATED)
def create_user(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud_user.create_user(db=db, user_data=user)

@router.get("/users/me", response_model=user_schema.User)
def read_users_me(current_user: user_model.User = Depends(get_current_active_user)):
    return current_user

@router.post("/companies", response_model=company_schema.Company, status_code=status.HTTP_201_CREATED)
def create_company(
    company: company_schema.CompanyCreate, 
    db: Session = Depends(get_db),
    # Proteger este endpoint (ej: solo admin)
    # current_user: user_model.User = Depends(get_current_active_user) 
):
    return crud_user.create_company(db=db, company_data=company)

@router.post("/companies/assign", status_code=status.HTTP_201_CREATED)
def assign_user_to_company(
    assignment: company_schema.CompanyAssignment,
    db: Session = Depends(get_db)
    # Proteger este endpoint
):
    # Aquí faltaría validar que el usuario y la empresa existan
    return crud_user.assign_user_to_company(db=db, assignment=assignment)

@router.get("/users/me/roles", response_model=List[UserRoleInCompany])
def read_user_roles(
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Obtiene una lista de todas las empresas y roles
    asignados al usuario actualmente autenticado.
    """
    
    # Hacemos una consulta que une la tabla de asociación con la de empresas
    # para obtener el nombre de la empresa y el rol.
    assignments = (
        db.query(
            association.UserCompany.company_id,
            company.Company.name.label("company_name"), # Ponemos una etiqueta para que coincida con el schema
            association.UserCompany.role
        )
        .join(
            company.Company,
            association.UserCompany.company_id == company.Company.id
        )
        .filter(association.UserCompany.user_id == current_user.id)
        .all()
    )
    
    return assignments