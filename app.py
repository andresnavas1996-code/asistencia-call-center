import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- 1. CONFIGURACIÓN ---
HORA_INICIO = time(0, 0)
HORA_FIN = time(23, 59)
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'

# Equipos iniciales (Solo se usan la primera vez para crear la base de datos)
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

# --- 2. FUNCIONES DEL SISTEMA ---

def inicializar_empleados():
    """Crea el archivo maestro de empleados si no existe."""
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        datos_lista = []
        for equipo, nombres in EQUIPOS_INICIALES.items():
            for nombre in nombres:
                datos_lista.append({
                    "Equipo": equipo, 
                    "Nombre": nombre, 
                    "Cedula": ""  # Campo nuevo vacío
                })
        df_base = pd.DataFrame(datos_lista)
        df_base.to_csv(ARCHIVO_EMPLEADOS, index=False)

def cargar_empleados(equipo_filtro):
    """Carga los empleados guardados de un equipo."""
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        inicializar_empleados()
    
    # Leemos todo como texto (dtype=str) para que la cédula no se dañe
    df_todos = pd.read_csv(ARCHIVO_EMPLEADOS, dtype=str)
    # Filtramos solo el equipo que necesitamos
    df_equipo = df_todos[df_todos['Equipo'] == equipo_filtro].copy()
    return df_equipo

def actualizar_base_empleados(df_nuevos_datos, equipo_actual):
    """Guarda a las personas nuevas para que no se borren mañana."""
    df_db = pd.read_csv(ARCHIVO_EMPLEADOS, dtype=str)
    
    cambios = False
    for index, row in df_nuevos_datos.iterrows():
        nombre = str(row['Nombre']).strip()
        cedula = str(row['Cedula']).strip()
        
        # Verificamos si ya existe esa persona en ese equipo
        existe = ((df_db['Nombre'] == nombre) & (df_db['Equipo'] == equipo_actual)).any()
        
        # Si no existe y tiene nombre, lo agregamos
        if not existe and nombre and nombre != "nan":
            nuevo = pd.DataFrame([{
                "Equipo": equipo_actual, 
                "Nombre": nombre, 
                "Cedula": cedula
            }])
            df_db = pd.concat([df_db, nuevo], ignore_index=True)
            cambios = True
            
    if cambios:
        df_db.to_csv(ARCHIVO_EMPLEADOS, index=False)

def guardar_asistencia_diaria(df_nuevo):
    """Guarda el reporte de asistencia del día."""
    if os.path.exists(ARCHIVO_ASISTENCIA):
        df_historico = pd.read_csv(ARCHIVO_ASISTENCIA, dtype=str)
    else:
        df_historico = pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion"])
        
    df_final = pd.concat([df_historico, df_nuevo], ignore_index=True)
    df_final.to_csv(ARCHIVO_ASISTENCIA, index=False)

# --- 3. INTERFAZ GRÁFICA ---
st.set_page_config(page_title="Asistencia Call Center", layout="wide")
st.title("📋 Malla de Asistencia - Base de Datos Dinámica")

# Aseguramos que exista la base de datos
inicializar_empleados()

tab_registro, tab_reporte = st.tabs(["⚡ Registrar Asistencia", "📊 Dashboard"])

# --- PESTAÑA DE REGISTRO ---
with tab_registro:
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        lista_equipos = list(EQUIPOS_INICIALES.keys())
        
        col_sel, _ = st.columns([1, 2])
        with col_sel:
            equipo_sel = st.selectbox("Selecciona tu Equipo:", lista_equipos)
            
        st.info("💡 Las personas nuevas que agregues abajo quedarán guardadas automáticamente en este equipo.")
        
        # 1. Traer empleados de la Base de Datos
        df_empleados = cargar_empleados(equipo_sel)
        
        # 2. Preparar tabla para editar (rellenamos Estado y Observación)
        df_input = df_empleados[['Nombre', 'Cedula']].copy()
        df_input['Estado'] = "Presente"
        df_input['Observacion'] = ""
        
        # 3. Mostrar el Editor con la columna CÉDULA
        df_editado = st.data_editor(
            df_input,
            column_config={
                "Nombre": st.column_config.TextColumn("Nombre Agente", required=True),
                "Cedula": st.column_config.TextColumn("Cédula / ID", required=True),
                "Estado": st.column_config.SelectboxColumn("Estado", options=["Presente", "Ausente", "Tarde", "Licencia", "Vacaciones"], required=True),
                "Observacion": st.column_config.TextColumn("Observación")
            },
            hide_index=True,
            num_rows="dynamic", # ¡Esto permite el botón '+'!
            use_container_width=True
        )
        
        # 4. Guardar
        if st.button("💾 Guardar Asistencia y Actualizar Personal"):
            if not df_editado.empty:
                # A) Actualizamos la base de datos de empleados (si hay nuevos)
                actualizar_base_empleados(df_editado, equipo_sel)
                
                # B) Guardamos la asistencia de hoy
                df_final = df_editado.copy()
                df_final["Fecha"] = datetime.now().strftime("%Y-%m-%d")
                df_final["Equipo"] = equipo_sel
                
                # Seleccionamos y ordenamos las columnas
                cols_ordenadas = ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion"]
                guardar_asistencia_diaria(df_final[cols_ordenadas])
                
                st.toast(f"✅ ¡Guardado! Se actualizaron los registros de {equipo_sel}.")
            else:
                st.warning("La tabla está vacía.")
    else:
        st.error(f"⛔ Sistema Cerrado por Horario ({HORA_INICIO} - {HORA_FIN})")

# --- PESTAÑA DE REPORTES ---
with tab_reporte:
    st.header("Histórico de Asistencias")
    if os.path.exists(ARCHIVO_ASISTENCIA):
        df = pd.read_csv(ARCHIVO_ASISTENCIA)
        st.metric("Total Registros", len(df))
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Aún no se han guardado asistencias.")
