import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- CONFIGURACIÓN ---
HORA_INICIO = time(0, 0)
HORA_FIN = time(23, 59)
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'

# Lista inicial (Solo se usará la primera vez para crear la base de datos)
EQUIPOS_INICIALES = {
    "Callcenter Bucaramanga": ["Ana", "Carlos", "Beatriz", "David"],
    "Callcenter Medellin": ["Elena", "Fernando", "Gabriela"],
    "Callcenter Bogota": ["Hugo", "Inés", "Javier"],
    "Servicio al cliente": ["Kevin", "Laura", "Marta"],
    "CallcenterMayoreo Medellin": ["Nancy", "Oscar", "Pablo"],
    "Campo 6": ["Empleado 1", "Empleado 2"],
    "Campo 7": ["Empleado A", "Empleado B"],
    "Campo 8": ["Persona X", "Persona Y"],
    "Campo 9": ["Agente 1", "Agente 2"],
    "Campo 10": ["Nombre 1", "Nombre 2"],
    "Campo 11": ["Test 1", "Test 2"]
}

# --- FUNCIONES DE BASE DE DATOS ---

def inicializar_empleados():
    """Crea el archivo de empleados si no existe, usando la lista inicial."""
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        datos_lista = []
        for equipo, nombres in EQUIPOS_INICIALES.items():
            for nombre in nombres:
                datos_lista.append({
                    "Equipo": equipo,
                    "Nombre": nombre,
                    "Cedula": "" # Cédula vacía para los antiguos
                })
        df_base = pd.DataFrame(datos_lista)
        df_base.to_csv(ARCHIVO_EMPLEADOS, index=False)

def cargar_empleados(equipo_filtro):
    """Carga los empleados de un equipo específico desde el archivo maestro."""
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        inicializar_empleados()
    
    df_todos = pd.read_csv(ARCHIVO_EMPLEADOS, dtype=str) # Leemos todo como texto para evitar errores
    df_equipo = df_todos[df_todos['Equipo'] == equipo_filtro].copy()
    return df_equipo

def actualizar_base_empleados(df_nuevos_datos, equipo_actual):
    """Detecta si hay gente nueva en el registro y la agrega a la base maestra."""
    df_db = pd.read_csv(ARCHIVO_EMPLEADOS, dtype=str)
    
    # Recorremos los datos que acabas de llenar
    cambios_realizados = False
    for index, row in df_nuevos_datos.iterrows():
        nombre = str(row['Nombre']).strip()
        cedula = str(row['Cedula']).strip()
        
        # Verificamos si esta persona (Nombre + Equipo) ya existe en la DB
        existe = ((df_db['Nombre'] == nombre) & (df_db['Equipo'] == equipo_actual)).any()
        
        if not existe and nombre and nombre != "nan":
            # Si no existe, lo agregamos
            nuevo_empleado = pd.DataFrame([{
                "Equipo": equipo_actual, 
                "Nombre": nombre, 
                "Cedula": cedula
            }])
            df_db = pd.concat([df_db, nuevo_empleado], ignore_index=True)
            cambios_realizados = True
            
    if cambios_realizados:
        df_db.to_csv(ARCHIVO_EMPLEADOS, index=False)

def guardar_asistencia(df_nuevo):
    if os.path.exists(ARCHIVO_ASISTENCIA):
        df_historico = pd.read_csv(ARCHIVO_ASISTENCIA)
    else:
        df_historico = pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion"])
        
    df_final = pd.concat([df_historico, df_nuevo], ignore_index=True)
    df_final.to_csv(ARCHIVO_ASISTENCIA, index=False)

# --- INTERFAZ ---
st.set_page_config(page_title="Control Asistencia", layout="wide")
st.title("📋 Malla de Asistencia - Base de Datos Dinámica")

# Inicializamos la DB si es la primera vez que corre
inicializar_empleados()

tab_registro, tab_reporte = st.tabs(["⚡ Registrar Asistencia", "📊 Dashboard"])

# --- PESTAÑA 1: REGISTRO ---
with tab_registro:
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        # Cargamos los equipos disponibles desde el archivo o la lista inicial
        lista_equipos = list(EQUIPOS_INICIALES.keys())
        
        col_sel, _ = st.columns([1, 2])
        with col_sel:
            equipo_sel = st.selectbox("Selecciona tu Equipo:", lista_equipos)
        
        st.info("💡 Si agregas una persona nueva abajo, el sistema la GUARDARÁ para siempre en este equipo.")
        
        # 1. Cargamos los empleados guardados de este equipo
        df_empleados = cargar_empleados(equipo_sel)
        
        # 2. Preparamos el DataFrame para la edición
        # Rellenamos columnas que faltan para el registro diario
        df_input = df_empleados[['Nombre', 'Cedula']].copy()
        df_input['Estado'] = "Presente"
        df_input['Observacion'] = ""
        
        # 3. El Editor
        df_editado = st.data_editor(
            df_input,
            column_config={
                "Nombre": st.column_config.TextColumn("Nombre Completo", required=True),
                "Cedula": st.column_config.TextColumn("Cédula / ID", required=True),
                "Estado": st.column_config.SelectboxColumn("Estado", options=["Presente", "Ausente", "Tarde", "Licencia", "Vacaciones"], required=True),
                "Observacion": st.column_config.TextColumn("Observación")
            },
            hide_index=True,
            num_rows="dynamic", # Permite agregar filas
            use_container_width=True,
            key="editor_asistencia"
        )
        
        # 4. Botón de Guardado
        if st.button("💾 Guardar Asistencia y Actualizar Personal"):
            if not df_editado.empty:
                # A) Primero actualizamos la base de datos de empleados (si hay nuevos)
                actualizar_base_empleados(df_editado, equipo_sel)
                
                # B) Luego guardamos la asistencia de hoy
                df_final = df_editado.copy()
                df_final["Fecha"] = datetime.now().strftime("%Y-%m-%d")
                df_final["Equipo"] = equipo_sel
                
                # Ordenar columnas
                cols = ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion"]
                guardar_asistencia(df_final[cols])
                
                st.toast(f"✅ Datos guardados. Si agregaste personal nuevo, ya quedó registrado.")
                
    else:
        st.error(f"⛔ Sistema Cerrado ({HORA_INICIO} - {HORA_FIN})")

# --- PESTAÑA 2: DASHBOARD ---
with tab_reporte:
    if os.path.
