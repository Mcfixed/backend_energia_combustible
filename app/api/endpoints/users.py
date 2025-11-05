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

@router.get("/users", response_model=List[user_schema.User])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # Proteger este endpoint (ej: solo admin)
    # current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Obtiene una lista de todos los usuarios.
    """
    users = crud_user.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/users/{user_id}", response_model=user_schema.User)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    # Proteger este endpoint
    # current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Obtiene un usuario específico por su ID.
    """
    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.patch("/users/{user_id}", response_model=user_schema.User)
def update_user(
    user_id: int,
    user_in: user_schema.UserUpdate,  # <-- Usa el nuevo schema
    db: Session = Depends(get_db),
    # Proteger (ej: admin o el propio usuario)
    # current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Actualiza un usuario (email, password, is_active).
    """
    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validar si el nuevo email ya existe
    if user_in.email:
        existing_user = crud_user.get_user_by_email(db, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Email already registered by another user")

    user = crud_user.update_user(db=db, db_user=db_user, user_in=user_in)
    return user

@router.delete("/users/{user_id}", response_model=user_schema.User)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    # Proteger (ej: solo admin)
    # current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Desactiva un usuario (Soft Delete).
    Esto es más seguro que un borrado físico.
    """
    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Preparamos un objeto UserUpdate para marcarlo como inactivo
    soft_delete_data = user_schema.UserUpdate(is_active=False)
    
    # Reutilizamos la función de actualizar para hacer el soft delete
    user = crud_user.update_user(db=db, db_user=db_user, user_in=soft_delete_data)
    return user

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









@router.post("/companies", response_model=company_schema.Company, status_code=status.HTTP_201_CREATED)
def create_company(
    company: company_schema.CompanyCreate, 
    db: Session = Depends(get_db),
    # Proteger este endpoint (ej: solo admin)
    # current_user: user_model.User = Depends(get_current_active_user) 
):
    return crud_user.create_company(db=db, company_data=company)

@router.get("/companies", response_model=List[company_schema.CompanyWithCenters])
def read_companies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # current_user: user_model.User = Depends(get_current_active_user) 
):
    """
    Obtiene una lista de todas las compañías, incluyendo sus centros.
    """
    companies = crud_user.get_companies(db, skip=skip, limit=limit)
    return companies
@router.get("/companies/{company_id}", response_model=company_schema.Company)
def read_company(
    company_id: int, 
    db: Session = Depends(get_db)
    # Proteger este endpoint
    # current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Obtiene una compañía específica por su ID.
    """
    db_company = crud_user.get_company_by_id(db, company_id=company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return db_company

@router.patch("/companies/{company_id}", response_model=company_schema.Company)
def update_company(
    company_id: int,
    company_in: company_schema.CompanyUpdate, # Usa el schema CompanyUpdate
    db: Session = Depends(get_db)
    # Proteger este endpoint (ej: solo admin)
    # current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Actualiza el nombre de una compañía.
    """
    db_company = crud_user.get_company_by_id(db, company_id=company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company = crud_user.update_company(db=db, db_company=db_company, company_in=company_in)
    return company

@router.delete("/companies/{company_id}", response_model=company_schema.Company)
def delete_company(
    company_id: int, 
    db: Session = Depends(get_db)
    # Proteger este endpoint (ej: solo admin)
    # current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Elimina una compañía de la base de datos.
    """
    db_company = crud_user.delete_company(db, company_id=company_id)
    if db_company is None:
        # delete_company devuelve None si no la encontró
        raise HTTPException(status_code=404, detail="Company not found")
    return db_company





@router.post("/companies/assign", status_code=status.HTTP_201_CREATED)
def assign_user_to_company(
    assignment: company_schema.CompanyAssignment,
    db: Session = Depends(get_db)
    # Proteger este endpoint
    # current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Asigna un usuario a una compañía con un rol específico.
    """
    
    db_user = crud_user.get_user_by_id(db, assignment.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found. Cannot assign.")
        
    db_company = crud_user.get_company_by_id(db, assignment.company_id)
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found. Cannot assign.")

    
    return crud_user.assign_user_to_company(db=db, assignment=assignment)



