from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from pydantic import BaseModel
from . import models, database
from .database import engine, SessionLocal
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Inicializar DB
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gestor de Turnos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción cambiar por la IP específica
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- Schemas (Validadores de entrada/salida) ---
class UserSchema(BaseModel):
    id: int
    full_name: str
    email: str
    class Config:
        orm_mode = True

class AllocationSchema(BaseModel):
    id: int
    date: date
    workstation_number: int
    user_name: str
    
    class Config:
        orm_mode = True

class SwapRequestCreate(BaseModel):
    requester_id: int
    target_allocation_id: int

# --- Dependencia para obtener la DB ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"message": "API de Turnos funcionando 🚀"}

@app.get("/users", response_model=List[UserSchema])
def get_users(db: Session = Depends(get_db)):
    """Obtener lista de compañeros"""
    return db.query(models.User).all()

@app.get("/allocations")
def get_matrix(db: Session = Depends(get_db)):
    """
    Devuelve la matriz de turnos. 
    Hacemos un 'join' manual simple para devolver datos legibles.
    """
    results = (
        db.query(models.Allocation, models.User, models.Workstation)
        .join(models.User, models.Allocation.user_id == models.User.id)
        .join(models.Workstation, models.Allocation.workstation_id == models.Workstation.id)
        .all()
    )
    
    # Transformamos a un JSON limpio
    data = []
    for alloc, user, ws in results:
        data.append({
            "id": alloc.id,
            "date": alloc.date,
            "user": user.full_name,
            "workstation": ws.number
        })
    return data

@app.post("/request-swap")
def request_swap(payload: SwapRequestCreate, db: Session = Depends(get_db)):
    """
    Crea una solicitud de intercambio SIN LÍMITE DE CRÉDITOS.
    Requisito: Ambos usuarios deben tener un puesto asignado ese día para hacer el enroque.
    """
    # 1. Buscar al solicitante
    requester = db.query(models.User).filter(models.User.id == payload.requester_id).first()
    if not requester:
        raise HTTPException(status_code=404, detail="Usuario solicitante no encontrado")
    
    # --- ELIMINADO: Chequeo de créditos (swap_credits) ---

    # 2. Buscar el turno destino (el que quieres tomar)
    target_alloc = db.query(models.Allocation).filter(models.Allocation.id == payload.target_allocation_id).first()
    if not target_alloc:
        raise HTTPException(status_code=404, detail="Turno destino no encontrado")

    if target_alloc.user_id == requester.id:
        raise HTTPException(status_code=400, detail="¡No puedes cambiarte contigo mismo!")

    # 3. Validar que TÚ tengas algo que ofrecer a cambio ese mismo día
    # Buscamos tu turno en la misma fecha del turno objetivo
    requester_alloc_same_day = db.query(models.Allocation).filter(
        models.Allocation.user_id == requester.id,
        models.Allocation.date == target_alloc.date
    ).first()

    if not requester_alloc_same_day:
        # Si no tienes turno, no es un intercambio, sería una "cesión" o "robo" de puesto.
        # Por ahora mantenemos la lógica de intercambio estricto.
        raise HTTPException(status_code=400, detail="No tienes puesto asignado ese día para hacer el trueque.")

    # 4. Verificar duplicados (para no spamear)
    existing = db.query(models.SwapRequest).filter(
        models.SwapRequest.requester_id == requester.id,
        models.SwapRequest.target_user_id == target_alloc.user_id,
        models.SwapRequest.target_date == target_alloc.date,
        models.SwapRequest.status == models.RequestStatus.PENDING
    ).first()

    if existing:
         raise HTTPException(status_code=400, detail="Ya enviaste una solicitud para este puesto.")

    # 5. Crear la Solicitud
    new_request = models.SwapRequest(
        requester_id=requester.id,
        target_user_id=target_alloc.user_id,
        target_date=target_alloc.date,
        status=models.RequestStatus.PENDING,
        created_at=str(date.today())
    )
    
    db.add(new_request)
    db.commit()
    
    return {"message": "✅ Propuesta de cambio enviada exitosamente."}