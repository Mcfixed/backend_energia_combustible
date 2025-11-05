# init_db.py
from app.db.database import Base, engine

from app.models.user import User
from app.models.company import Company
from app.models.association import UserCompany
from app.models.center import Center  
from app.models.device import Device 

def reset_database():
    print("Eliminando todas las tablas...")
    Base.metadata.drop_all(bind=engine)
    print("Tablas eliminadas.")
    
    print("Creando todas las tablas nuevas...")
    Base.metadata.create_all(bind=engine)
    print("¡Base de datos creada exitosamente!")

if __name__ == "__main__":
    print("ADVERTENCIA: Esto eliminará TODOS los datos y recreará la base de datos.")
    confirm = input("¿Estás seguro? Escribe 'si' para continuar: ")
    
    if confirm.lower() == 'si':
        reset_database()
    else:
        print("Operación cancelada.")