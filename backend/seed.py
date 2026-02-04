import pandas as pd
import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, Workstation, Allocation

# 1. Crear las tablas en la BD
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def parse_date(date_str, year=2026):
    """Convierte 'Lunes 02/02' a objeto date 2026-02-02"""
    match = re.search(r'(\d{2})/(\d{2})', str(date_str))
    if match:
        day, month = match.groups()
        return datetime(year, int(month), int(day)).date()
    return None

def seed_data():
    db = SessionLocal()
    print("🔄 Iniciando carga masiva de datos...")
    
    # Limpiar datos anteriores (Opcional, cuidado en prod)
    db.query(Allocation).delete()
    db.query(Workstation).delete()
    db.query(User).delete()
    db.commit()

    file_path = 'Planificacion_Febrero_2026.csv' # Asegúrate que el nombre coincida
    try:
        df_raw = pd.read_csv(file_path, header=None)
    except FileNotFoundError:
        print(f"Error: No se encuentra {file_path}")
        return

    users_cache = {} # Cache para no consultar la DB a cada rato
    workstations_cache = {}

    # Lógica de Parsing del Excel "Sucio"
    current_row = 0
    total_allocations = 0

    while current_row < len(df_raw):
        row_data = df_raw.iloc[current_row]
        first_col = str(row_data[0])

        if "SEMANA" in first_col:
            print(f"Procesando bloque: {first_col}")
            
            # La fila siguiente tiene las fechas
            header_row = df_raw.iloc[current_row + 1]
            date_map = {} # {col_index: python_date}
            
            for col_idx in range(2, 7): # Asumimos columnas C a G (días de la semana)
                raw_date = header_row[col_idx]
                parsed_date = parse_date(raw_date)
                if parsed_date:
                    date_map[col_idx] = parsed_date
            
            # Iteramos las filas de datos de esta semana
            data_cursor = current_row + 2
            while data_cursor < len(df_raw):
                puesto_val = df_raw.iloc[data_cursor, 1]
                
                # Si no hay puesto válido, se acabó el bloque
                if pd.isna(puesto_val) or str(puesto_val).strip() == '':
                    break
                
                puesto_num = int(puesto_val)
                
                # 1. Crear/Recuperar Puesto
                if puesto_num not in workstations_cache:
                    ws = Workstation(number=puesto_num, description=f"Puesto {puesto_num}")
                    db.add(ws)
                    db.commit()
                    db.refresh(ws)
                    workstations_cache[puesto_num] = ws.id
                
                ws_id = workstations_cache[puesto_num]

                # 2. Iterar días
                for col_idx, date_obj in date_map.items():
                    user_name = df_raw.iloc[data_cursor, col_idx]
                    
                    # Validar que sea un nombre real
                    if pd.notna(user_name) and str(user_name) not in ['X', 'Libre', 'nan']:
                        user_name = str(user_name).strip()
                        
                        # 3. Crear/Recuperar Usuario
                        if user_name not in users_cache:
                            # Creamos email dummy
                            dummy_email = f"{user_name.lower().replace(' ', '.')}@empresa.com"
                            new_user = User(
                                full_name=user_name,
                                email=dummy_email,
                                hashed_password="hashed_secret_123", # TODO: Usar hash real después
                                swap_credits=3
                            )
                            db.add(new_user)
                            db.commit()
                            db.refresh(new_user)
                            users_cache[user_name] = new_user.id
                        
                        u_id = users_cache[user_name]

                        # 4. Crear Asignación
                        allocation = Allocation(
                            date=date_obj,
                            user_id=u_id,
                            workstation_id=ws_id
                        )
                        db.add(allocation)
                        total_allocations += 1
                
                data_cursor += 1
            
            # Saltamos el cursor principal al final de este bloque
            current_row = data_cursor
        else:
            current_row += 1

    db.commit()
    print(f"Carga completa: {len(users_cache)} usuarios, {len(workstations_cache)} puestos, {total_allocations} asignaciones creadas.")
    db.close()

if __name__ == "__main__":
    seed_data()