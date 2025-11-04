# init_db.py
from app.db.database import Base, engine

# --- ¡MUY IMPORTANTE! ---
# Importa aquí TODOS tus modelos para que SQLAlchemy los "vea"
# y sepa que debe crearlos.
from app.models.user import User
from app.models.company import Company
from app.models.association import UserCompany
from app.models.center import Center  # El nuevo modelo
from app.models.device import Device  # El modelo actualizado

def reset_database():
    print("Eliminando todas las tablas...")
    # Borra todas las tablas existentes
    Base.metadata.drop_all(bind=engine)
    print("Tablas eliminadas.")
    
    print("Creando todas las tablas nuevas...")
    # Crea todas las tablas basadas en tus modelos
    Base.metadata.create_all(bind=engine)
    print("¡Base de datos creada exitosamente!")

if __name__ == "__main__":
    # Esto te dará una última oportunidad para cancelar
    print("ADVERTENCIA: Esto eliminará TODOS los datos y recreará la base de datos.")
    confirm = input("¿Estás seguro? Escribe 'si' para continuar: ")
    
    if confirm.lower() == 'si':
        reset_database()
    else:
        print("Operación cancelada.")