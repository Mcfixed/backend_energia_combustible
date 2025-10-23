from sqlalchemy.orm import Session
from app.models import user, company, association
from app.schemas import user as user_schema, company as company_schema
from app.core.security import get_password_hash

def get_user_by_email(db: Session, email: str) -> user.User | None:
    return db.query(user.User).filter(user.User.email == email).first()

def create_user(db: Session, user_data: user_schema.UserCreate) -> user.User:
    hashed_password = get_password_hash(user_data.password)
    db_user = user.User(email=user_data.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_company(db: Session, company_data: company_schema.CompanyCreate) -> company.Company:
    db_company = company.Company(name=company_data.name)
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

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