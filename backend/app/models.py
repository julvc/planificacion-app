from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from .database import Base
import enum

# Constants for table references
USERS_TABLE = "users.id"

# Enums para controlar estados sin "magic strings"
class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True) # Nombre completo del CSV
    email = Column(String, unique=True, index=True) # Generaremos emails dummy si no hay
    hashed_password = Column(String)
    
    # Lógica de negocio: Créditos para limitar cambios
    swap_credits = Column(Integer, default=3) 
    
    # Relaciones
    allocations = relationship("Allocation", back_populates="user")
    sent_requests = relationship("SwapRequest", foreign_keys="[SwapRequest.requester_id]", back_populates="requester")
    received_requests = relationship("SwapRequest", foreign_keys="[SwapRequest.target_user_id]", back_populates="target_user")

class Workstation(Base):
    __tablename__ = "workstations"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True) # El número "24", "25", etc.
    description = Column(String, nullable=True) # "Lado ventana", etc.

    allocations = relationship("Allocation", back_populates="workstation")

class Allocation(Base):
    """
    Tabla pivote normalizada.
    Convierte tu Excel visual en datos consultables:
    "El 02/02, Julio Varas está en el puesto 25"
    """
    __tablename__ = "allocations"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    
    user_id = Column(Integer, ForeignKey(USERS_TABLE))
    workstation_id = Column(Integer, ForeignKey("workstations.id"))

    user = relationship("User", back_populates="allocations")
    workstation = relationship("Workstation", back_populates="allocations")

class SwapRequest(Base):
    __tablename__ = "swap_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"))
    target_user_id = Column(Integer, ForeignKey("users.id"))
    verification_code = Column(String)
    # --- CAMBIO IMPORTANTE ---
    # Guardamos las dos fechas involucradas en el trueque
    requester_date = Column(Date) # La fecha que tú entregas
    target_date = Column(Date)    # La fecha que tú quieres recibir
    # -------------------------

    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    created_at = Column(String) 

    requester = relationship("User", foreign_keys=[requester_id], back_populates="sent_requests")
    target_user = relationship("User", foreign_keys=[target_user_id], back_populates="received_requests")

    