# 📅 Gestor de Turnos y Puestos - Backend

Sistema desarrollado en **FastAPI (Python)** y **Vue.js** para la gestión e intercambio de puestos de trabajo en el área de informática.

## 🚀 Requisitos

* Python 3.10 o superior
* Pip (Gestor de paquetes de Python)
* Virtualenv (Recomendado)

## 🛠️ Instalación y Configuración

1.  **Clonar/Entrar en la carpeta del backend:**
    ```bash
    cd backend
    ```

2.  **Crear entorno virtual:**
    ```bash
    python -m venv venv
    # En Windows:
    venv\Scripts\activate
    # En Mac/Linux:
    source venv/bin/activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install fastapi uvicorn sqlalchemy pydantic passlib[bcrypt] python-jose python-multipart pandas
    ```

## 💾 Carga de Datos (Seed)

El sistema incluye un script para importar la planilla Excel de planificación automáticamente a la base de datos.

1.  Asegúrate de que el archivo `Planificacion_Febrero_2026.csv` esté en la carpeta `backend/`.
2.  Ejecuta el script de carga:
    ```bash
    python seed.py
    ```
    *Esto creará el archivo `sql_app.db` (SQLite) con los usuarios, puestos y turnos cargados.*

## ▶️ Ejecución del Servidor

Para que el equipo pueda acceder desde su propia red, ejecutamos el servidor escuchando en `0.0.0.0`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

### 2. Script de Carga Masiva (`seed.py`)
Guarda este archivo en la carpeta `backend/` (al mismo nivel que la carpeta `app/`).

Este script es "inteligente":
1.  Lee el CSV sucio.
2.  Normaliza los nombres.
3.  Crea usuarios si no existen (con password default `1234`).
4.  Crea los puestos.
5.  Asigna los turnos por fecha.

**Nota:** Necesitas crear primero el archivo `backend/app/database.py` básico para que esto funcione. Te lo incluyo al inicio del bloque por si acaso.

#### A. Pre-requisito: `backend/app/database.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()