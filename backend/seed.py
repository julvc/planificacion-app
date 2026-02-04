import pandas as pd
import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, Workstation, Allocation

# Crear tablas
Base.metadata.create_all(bind=engine)

def parse_date(date_str, year=2026):
    match = re.search(r'(\d{1,2})/(\d{2})', str(date_str))
    if match:
        day, month = match.groups()
        return datetime(year, int(month), int(day)).date()
    return None

def seed_data():
    db = SessionLocal()
    print("🔄 Iniciando carga masiva de datos (V2 Corregida)...")
    
    # Limpiar todo
    db.query(Allocation).delete()
    db.query(Workstation).delete()
    db.query(User).delete()
    db.commit()

    try:
        # header=None es clave para leerlo por coordenadas
        df_raw = pd.read_excel('Planificacion_Febrero_2026.xlsx', header=None)
    except FileNotFoundError:
        print("❌ Error: No se encuentra el archivo .xlsx")
        return

    users_cache = {}
    workstations_cache = {}
    total_allocations = 0

    current_row = 0
    while current_row < len(df_raw):
        first_col = str(df_raw.iloc[current_row, 0])

        if "SEMANA" in first_col:
            print(f"📅 Detectado bloque: {first_col[:30]}...")
            
            # CORRECCIÓN: Las fechas están en esta MISMA fila, columnas 2 a 6 (C a G)
            header_row = df_raw.iloc[current_row]
            date_map = {} 
            
            for col_idx in range(2, 7): 
                raw_date = header_row[col_idx]
                parsed_date = parse_date(raw_date)
                if parsed_date:
                    date_map[col_idx] = parsed_date
            
            # Los datos de empleados empiezan en la fila siguiente
            data_cursor = current_row + 1
            
            while data_cursor < len(df_raw):
                puesto_val = df_raw.iloc[data_cursor, 1] # Columna B es Puesto
                
                # Si llegamos a una fila vacía o nueva semana, paramos
                first_col_next = str(df_raw.iloc[data_cursor, 0])
                if "SEMANA" in first_col_next:
                    break
                if pd.isna(puesto_val) or str(puesto_val).strip() == '':
                    # A veces hay filas vacías intermedias, si también está vacía la col 0, salimos
                    if pd.isna(df_raw.iloc[data_cursor, 0]):
                         data_cursor += 1
                         continue
                    else:
                         # Si es texto basura, seguimos
                         pass

                # Intentamos leer el puesto
                try:
                    puesto_num = int(float(puesto_val)) # float por si pandas leyó 18.0
                except (ValueError, TypeError):
                    data_cursor += 1
                    continue

                # 1. Gestionar Puesto
                if puesto_num not in workstations_cache:
                    ws = Workstation(number=puesto_num, description=f"Puesto {puesto_num}")
                    db.add(ws)
                    db.commit()
                    db.refresh(ws)
                    workstations_cache[puesto_num] = ws.id
                
                ws_id = workstations_cache[puesto_num]

                # 2. Gestionar Personas en las fechas detectadas
                for col_idx, date_obj in date_map.items():
                    user_name = df_raw.iloc[data_cursor, col_idx]
                    
                    if pd.notna(user_name) and str(user_name).strip() not in ['X', 'Libre', 'nan', 'Change']:
                        name_clean = str(user_name).strip()
                        
                        if name_clean not in users_cache:
                            dummy_email = f"{name_clean.lower().replace(' ', '.')}@dev.com"
                            new_user = User(
                                full_name=name_clean, 
                                email=dummy_email, 
                                hashed_password="123",
                                swap_credits=5
                            )
                            db.add(new_user)
                            db.commit()
                            db.refresh(new_user)
                            users_cache[name_clean] = new_user.id
                        
                        # Crear asignación
                        alloc = Allocation(
                            date=date_obj,
                            user_id=users_cache[name_clean],
                            workstation_id=ws_id
                        )
                        db.add(alloc)
                        total_allocations += 1

                data_cursor += 1
            
            # Avanzamos el cursor principal
            current_row = data_cursor
        else:
            current_row += 1

    db.commit()
    print(f"✅ ¡Éxito! {len(users_cache)} usuarios, {len(workstations_cache)} puestos, {total_allocations} turnos cargados.")
    db.close()

if __name__ == "__main__":
    seed_data()