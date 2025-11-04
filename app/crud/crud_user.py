from sqlalchemy.orm import Session, joinedload
from app.models import user, company, association, center
from app.schemas import user as user_schema, company as company_schema, center as center_schema
from app.core.security import get_password_hash
from typing import List

def get_user_by_email(db: Session, email: str) -> user.User | None:
    return db.query(user.User).filter(user.User.email == email).first()

def create_user(db: Session, user_data: user_schema.UserCreate) -> user.User:
    hashed_password = get_password_hash(user_data.password)
    db_user = user.User(email=user_data.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user



def assign_user_to_company(db: Session, assignment: company_schema.CompanyAssignment) -> association.UserCompany:
    db_assignment = association.UserCompany(
        user_id=assignment.user_id,
        company_id=assignment.company_id,
        role=assignment.role
    )
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment









#users nuevo
def get_user_by_id(db: Session, user_id: int) -> user.User | None:
    """Obtiene un usuario por su ID."""
    return db.query(user.User).filter(user.User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[user.User]:
    """Obtiene una lista de usuarios con paginación."""
    return db.query(user.User).offset(skip).limit(limit).all()

def update_user(
    db: Session, 
    db_user: user.User, 
    user_in: user_schema.UserUpdate
) -> user.User:
    """
    Actualiza un usuario.
    Usa model_dump(exclude_unset=True) para actualizar solo los campos enviados.
    """
    # Convierte el schema Pydantic a un dict, excluyendo campos no enviados
    update_data = user_in.model_dump(exclude_unset=True)

    # Si se envió 'password', hashearlo antes de guardarlo
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        db_user.hashed_password = hashed_password
        del update_data["password"]  # Eliminarlo del dict para no asignarlo en texto plano

    # Asignar los valores restantes (ej: email, is_active)
    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user_db(db: Session, user_id: int) -> user.User | None:
    """
    Elimina (borrado físico) un usuario de la base de datos por su ID.
    """
    db_user = db.query(user.User).filter(user.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user



# --- FUNCIONES DE COMPANY (Actualizadas y Añadidas) ---

def get_company_by_id(db: Session, company_id: int) -> company.Company | None:
    """Obtiene una compañía por su ID."""
    return db.query(company.Company).filter(company.Company.id == company_id).first()

def create_company(db: Session, company_data: company_schema.CompanyCreate) -> company.Company:
    db_company = company.Company(name=company_data.name)
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

def get_companies(db: Session, skip: int = 0, limit: int = 100) -> List[company.Company]:
    """
    Obtiene una lista de todas las compañías,
    cargando anticipadamente sus centros (centers).
    """
    return (
        db.query(company.Company)
        .options(joinedload(company.Company.centers)) # <-- ESTA LÍNEA ES LA MAGIA
        .offset(skip)
        .limit(limit)
        .all()
    )

def update_company(
    db: Session, 
    db_company: company.Company, 
    company_in: company_schema.CompanyUpdate
) -> company.Company:
    """Actualiza una compañía."""
    # Obtiene los datos del schema Pydantic que fueron enviados (no None)
    update_data = company_in.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_company, field, value)
    
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

def delete_company(db: Session, company_id: int) -> company.Company | None:
    """Elimina una compañía."""
    db_company = db.query(company.Company).filter(company.Company.id == company_id).first()
    if db_company:
        # NOTA: Si tienes centros asociados, esto podría fallar
        # si no tienes configurado 'on delete cascade' en tu modelo/relación.
        db.delete(db_company)
        db.commit()
    return db_company


# --- FUNCIONES DE CENTER (NUEVAS) ---

def create_center(db: Session, center_data: center_schema.CenterCreate) -> center.Center:
    """Crea un nuevo centro asociado a una compañía."""
    db_center = center.Center(
        name=center_data.name, 
        company_id=center_data.company_id
    )
    db.add(db_center)
    db.commit()
    db.refresh(db_center)
    return db_center

def get_center_by_id(db: Session, center_id: int) -> center.Center | None:
    """Obtiene un centro por su ID."""
    return db.query(center.Center).filter(center.Center.id == center_id).first()

def get_centers_by_company(db: Session, company_id: int) -> List[center.Center]:
    """Obtiene todos los centros de una compañía específica."""
    return db.query(center.Center).filter(center.Center.company_id == company_id).all()

def update_center(
    db: Session,
    db_center: center.Center,
    center_in: center_schema.CenterUpdate
) -> center.Center:
    """Actualiza un centro."""
    update_data = center_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_center, field, value)
    
    db.add(db_center)
    db.commit()
    db.refresh(db_center)
    return db_center

def delete_center(db: Session, center_id: int) -> center.Center | None:
    """Elimina un centro."""
    db_center = db.query(center.Center).filter(center.Center.id == center_id).first()
    if db_center:
        db.delete(db_center)
        db.commit()
    return db_center