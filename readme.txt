#####################crear entorno
py -3.10 -m venv venv
#activar
.\venv\Scripts\activate
pip install -r requirements.txt
#desactivar
deactivate



#activar backend 
uvicorn app.main:app --reload


crear tabla en base de datos MANUALMENTE DESPUES
alembic revision --autogenerate -m "Modelos iniciales"
alembic upgrade head 