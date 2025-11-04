from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud import crud_user  # Seguimos usando crud_user donde pusimos las funciones
from app.schemas import center as center_schema
from typing import List
# from app.api.dependencies import get_current_active_user # Para proteger endpoints

router = APIRouter()

@router.post("/centers", response_model=center_schema.Center, status_code=status.HTTP_201_CREATED)
def create_center(
    center: center_schema.CenterCreate,
    db: Session = Depends(get_db)
    # current_user: user_model.User = Depends(get_current_active_user) 
):
    # Validar que la compañía existe
    db_company = crud_user.get_company_by_id(db, company_id=center.company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found. Cannot create center.")
        
    return crud_user.create_center(db=db, center_data=center)


@router.get("/companies/{company_id}/centers", response_model=List[center_schema.Center])
def read_centers_for_company(
    company_id: int,
    db: Session = Depends(get_db)
    # current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Obtiene una lista de todos los centros para una compañía específica.
    """
    # Validar que la compañía existe
    db_company = crud_user.get_company_by_id(db, company_id=company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found.")
        
    centers = crud_user.get_centers_by_company(db, company_id=company_id)
    return centers

@router.patch("/centers/{center_id}", response_model=center_schema.Center)
def update_center(
    center_id: int,
    center_in: center_schema.CenterUpdate,
    db: Session = Depends(get_db)
    # current_user: user_model.User = Depends(get_current_active_user)
):
    db_center = crud_user.get_center_by_id(db, center_id=center_id)
    if db_center is None:
        raise HTTPException(status_code=404, detail="Center not found")
    
    center = crud_user.update_center(db=db, db_center=db_center, center_in=center_in)
    return center

@router.delete("/centers/{center_id}", response_model=center_schema.Center)
def delete_center(
    center_id: int,
    db: Session = Depends(get_db)
    # current_user: user_model.User = Depends(get_current_active_user)
):
    db_center = crud_user.delete_center(db, center_id=center_id)
    if db_center is None:
        raise HTTPException(status_code=404, detail="Center not found")
    return db_center