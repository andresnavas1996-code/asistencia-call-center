import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- 1. CONFIGURACIÓN ---
HORA_INICIO = time(0, 0)
HORA_FIN = time(23, 59)
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'

# Equipos iniciales (Solo para crear el archivo la primera vez)
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

# --- 2. FUNCIONES ---

def asegurar_archivos():
    """Crea los archivos CSV vacíos si no existen."""
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        datos_lista = []
        for equipo, nombres in EQUIPOS_INICIALES.items():
            for nombre in nombres:
                datos_lista.append({"Equipo": equipo, "Nombre": nombre, "Cedula": ""})
        pd.DataFrame(datos_lista).to_csv(ARCHIVO_EMPLEADOS, index=False)
    
    if not os.path.exists(ARCHIVO_ASISTENCIA):
        pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion"]).to_csv(ARCHIVO_ASISTENCIA, index=False)

def cargar_csv(archivo):
    """Carga un CSV y maneja errores."""
    asegurar_archivos()
    try:
        return pd.read_csv(archivo, dtype=str, keep_default_na=False)
    except:
        return pd.DataFrame()

def guardar_personal(df_nuevo, equipo_actual):
    """Sobrescribe los datos del equipo seleccionado en la base maestra."""
    df_todos = cargar_csv(ARCHIVO_EMPLEADOS)
    
    # 1. Eliminamos los datos viejos de ESTE equipo
    df_todos = df_todos[df_todos['Equipo'] != equipo_actual]
    
    # 2. Preparamos los nuevos datos (Aseguramos que tengan la columna Equipo)
    df_nuevo['Equipo'] = equipo_actual
    
    # 3. Unimos y guardamos
    df_final = pd.concat([df_todos, df_nuevo], ignore_index=True)
    df_final.to_csv(ARCHIVO_EMPLEADOS, index=False)

def guardar_asistencia(df_registro):
    """Agrega el reporte del día al historial."""
    df_historico = cargar_csv(ARCHIVO_ASISTENCIA)
    df_final = pd.concat([df_historico, df_registro], ignore_index=True)
    df_final.to_csv(ARCHIVO_ASISTENCIA, index=False)

# --- 3. INTERFAZ ---
st.set_page_config(page_title="Gestión Asistencia", layout="wide")
st.title("📋 Sistema Integral de Asistencia")

# Aseguramos que existan los archivos antes de empezar
asegurar_archivos()

# PESTAÑAS SEPARADAS
tab_personal, tab_asistencia, tab_reporte = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "📊 HISTÓRICO"])

# ==========================================
# PESTAÑA 1: GESTIÓN DE PERSONAL (Base de Datos)
# ==========================================
with tab_personal:
    st.header("Actualización de Base de Datos")
    st.info("Aquí puedes agregar personas nuevas, borrar antiguos o corregir cédulas. Estos cambios se guardan para el futuro.")
    
    equipo_gest = st.selectbox("Selecciona Equipo a Editar:", list(EQUIPOS_INICIALES.keys()), key="sel_gest")
    
    # Cargar datos actuales
    df_db = cargar_csv(ARCHIVO_EMPLEADOS)
    df_equipo = df_db[df_db['Equipo'] == equipo_gest][['Nombre', 'Cedula']]
    
    # Editor editable (Permite agregar/borrar filas)
    df_editado_personal = st.data_editor(
        df_equipo,
        column_config={
            "Nombre": st.column_config.TextColumn("Nombre Completo", required=True),
            "Cedula": st.column_config.TextColumn("Cédula", required=True)
        },
        num_rows="dynamic", # Permite añadir filas
        use_container_width=True,
        key="editor_personal"
    )
    
    if st.button("💾 ACTUALIZAR BASE DE DATOS", type="primary"):
        guardar_personal(df_editado_personal, equipo_gest)
        st.success(f"✅ Base de datos de {equipo_gest} actualizada correctamente.")
        st.rerun() # Recarga para asegurar que se vea el cambio

# ==========================================
# PESTAÑA 2: TOMAR ASISTENCIA (Diaria)
# ==========================================
with tab_asistencia:
    st.header("Registro Diario")
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        equipo_asist = st.selectbox("Selecciona Equipo:", list(EQUIPOS_INICIALES.keys()), key="sel_asist")
        
        # Cargar personal de la base de datos (SOLO LECTURA DE NOMBRES)
        df_db = cargar_csv(ARCHIVO_EMPLEADOS)
        df_personal_base = df_db[df_db['Equipo'] == equipo_asist]
        
        if df_personal_base.empty:
            st.warning("⚠️ Este equipo no tiene personal registrado. Ve a la pestaña 'Gestionar Personal' primero.")
        else:
            # Preparamos la tabla de asistencia
            df_input = df_personal_base[['Nombre', 'Cedula']].copy()
            df_input['Estado'] = "Presente"
            df_input['Observacion'] = ""
            
            st.write(f"Gestionando: **{equipo_asist}**")
            
            # Editor de asistencia (Nombres bloqueados, solo cambia estado)
            df_asistencia_final = st.data_editor(
                df_input,
                column_config={
                    "Nombre": st.column_config.Column(disabled=True), # Bloqueado
                    "Cedula": st.column_config.Column(disabled=True), # Bloqueado
                    "Estado": st.column_config.SelectboxColumn("Estado", options=["Asiste", "Ausente", "Llegada tarde", "Incapacidad", "Vacaciones"], required=True),
                    "Observacion": st.column_config.TextColumn("Observación")
                },
                hide_index=True,
                use_container_width=True,
                key="editor_asistencia"
            )
            
            if st.button("💾 GUARDAR ASISTENCIA DEL DÍA"):
                # Agregamos fecha y equipo
                df_guardar = df_asistencia_final.copy()
                df_guardar['Fecha'] = datetime.now().strftime("%Y-%m-%d")
                df_guardar['Equipo'] = equipo_asist
                
                # Ordenamos columnas
                guardar_asistencia(df_guardar[['Fecha', 'Equipo', 'Nombre', 'Cedula', 'Estado', 'Observacion']])
                st.toast("✅ Asistencia guardada con éxito.")

    else:
        st.error(f"⛔ Sistema Cerrado. Horario: {HORA_INICIO} - {HORA_FIN}")

# ==========================================
# PESTAÑA 3: HISTÓRICO
# ==========================================
with tab_reporte:
    st.header("Reportes Históricos")
    df_hist = cargar_csv(ARCHIVO_ASISTENCIA)
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True)
        st.metric("Total Registros", len(df_hist))
    else:
        st.info("No hay registros de asistencia todavía.")
