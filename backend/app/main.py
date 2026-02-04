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
    offer_allocation_id: int  # El ID de tu turno (origen)
    target_allocation_id: int # El ID del turno que quieres (destino)

class SwapResponse(BaseModel):
    request_id: int
    action: str  # "ACCEPT" o "REJECT"

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
    Intercambio cruzado: "Te doy mi día X por tu día Y".
    """
    # 1. Validar Solicitante
    requester = db.query(models.User).filter(models.User.id == payload.requester_id).first()
    if not requester:
        raise HTTPException(status_code=404, detail="Usuario solicitante no encontrado")

    # 2. Validar TU oferta (Debe ser un turno tuyo)
    offer_alloc = db.query(models.Allocation).filter(models.Allocation.id == payload.offer_allocation_id).first()
    if not offer_alloc:
        raise HTTPException(status_code=404, detail="Tu turno ofertado no existe")
    if offer_alloc.user_id != requester.id:
        raise HTTPException(status_code=403, detail="El turno que ofreces no te pertenece")

    # 3. Validar el objetivo (Debe ser de otro)
    target_alloc = db.query(models.Allocation).filter(models.Allocation.id == payload.target_allocation_id).first()
    if not target_alloc:
        raise HTTPException(status_code=404, detail="El turno destino no existe")
    if target_alloc.user_id == requester.id:
        raise HTTPException(status_code=400, detail="No puedes intercambiar contigo mismo")

    # 4. Validar duplicados (Evitar doble solicitud para el mismo par de fechas)
    existing = db.query(models.SwapRequest).filter(
        models.SwapRequest.requester_id == requester.id,
        models.SwapRequest.target_user_id == target_alloc.user_id,
        models.SwapRequest.requester_date == offer_alloc.date, # Fecha A
        models.SwapRequest.target_date == target_alloc.date,   # Fecha B
        models.SwapRequest.status == models.RequestStatus.PENDING
    ).first()

    if existing:
            raise HTTPException(status_code=400, detail="Ya existe una solicitud pendiente idéntica.")

    # 5. Crear la Solicitud Cruzada
    new_request = models.SwapRequest(
        requester_id=requester.id,
        target_user_id=target_alloc.user_id,
        requester_date=offer_alloc.date, # Guardo mi fecha
        target_date=target_alloc.date,   # Guardo su fecha
        status=models.RequestStatus.PENDING,
        created_at=str(date.today())
    )
    
    db.add(new_request)
    db.commit()
    
    return {
        "message": f"✅ Propuesta enviada: Tu turno del {offer_alloc.date} ⟷ Turno de {target_alloc.user.full_name} del {target_alloc.date}"
    }

@app.get("/pending-requests/{user_id}")
def get_pending_requests(user_id: int, db: Session = Depends(get_db)):
    """
    Obtiene las solicitudes que ME han enviado a mí y están pendientes.
    Incluimos los datos del solicitante para mostrar "Julio quiere cambiar..."
    """
    requests = db.query(models.SwapRequest).filter(
        models.SwapRequest.target_user_id == user_id,
        models.SwapRequest.status == models.RequestStatus.PENDING
    ).all()
    
    # Enriquecemos la respuesta manualmente para el frontend
    result = []
    for r in requests:
        result.append({
            "id": r.id,
            "requester_name": r.requester.full_name,
            "requester_date": r.requester_date,
            "my_date": r.target_date,
            "status": r.status
        })
    return result

@app.post("/process-swap")
def process_swap(payload: SwapResponse, db: Session = Depends(get_db)):
    """
    El momento de la verdad. Si es ACCEPT, intercambiamos los turnos.
    """
    # 1. Buscar la solicitud
    req = db.query(models.SwapRequest).filter(models.SwapRequest.id == payload.request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if req.status != models.RequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Esta solicitud ya fue procesada")

    # 2. Lógica de Rechazo
    if payload.action == "REJECT":
        req.status = models.RequestStatus.REJECTED
        db.commit()
        return {"message": "Solicitud rechazada."}

    # 3. Lógica de Aceptación (El Intercambio Real)
    if payload.action == "ACCEPT":
        # Buscamos los DOS turnos en la tabla Allocation usando las fechas y usuarios guardados
        
        # Turno A: El que ERA del solicitante (en fecha origen)
        alloc_origin = db.query(models.Allocation).filter(
            models.Allocation.user_id == req.requester_id,
            models.Allocation.date == req.requester_date
        ).first()

        # Turno B: El que ES del receptor (en fecha destino)
        alloc_target = db.query(models.Allocation).filter(
            models.Allocation.user_id == req.target_user_id,
            models.Allocation.date == req.target_date
        ).first()

        if not alloc_origin or not alloc_target:
                req.status = models.RequestStatus.CANCELLED
                db.commit()
                raise HTTPException(status_code=400, detail="Uno de los turnos ya no existe o cambió. Solicitud cancelada.")

        # --- EL INTERCAMBIO (SWAP) ---
        # Guardamos temporalmente el ID del dueño A
        temp_user_id = alloc_origin.user_id
        
        # Asignamos: Turno A ahora es de B
        alloc_origin.user_id = alloc_target.user_id
        
        # Asignamos: Turno B ahora es de A
        alloc_target.user_id = temp_user_id

        # Actualizamos estado de la solicitud
        req.status = models.RequestStatus.ACCEPTED
        
        db.commit()
        return {"message": "✅ ¡Intercambio realizado con éxito! La tabla se ha actualizado."}