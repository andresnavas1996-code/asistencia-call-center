import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- 1. CONFIGURACIÓN DE EQUIPOS ---
# Nota: Para los equipos grandes, puedes pegar aquí todos los nombres entre comillas.
EQUIPOS = {
    "Callcenter Bucaramanga": ["Ana", "Carlos", "Beatriz", "David"], # Agrega aquí hasta las 38 personas
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

# Configuración del horario (Extendido para pruebas)
HORA_INICIO = time(0, 0)
HORA_FIN = time(23, 59)
ARCHIVO_DATOS = 'asistencia_historica.csv'

# --- 2. FUNCIONES DE CARGA Y GUARDADO ---
def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        return pd.read_csv(ARCHIVO_DATOS)
    else:
        return pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Estado", "Observacion"])

def guardar_asistencia(df_nuevo):
    df_historico = cargar_datos()
    df_final = pd.concat([df_historico, df_nuevo], ignore_index=True)
    df_final.to_csv(ARCHIVO_DATOS, index=False)
    return df_final

# --- 3. INTERFAZ DE USUARIO ---
st.set_page_config(page_title="Control de Asistencia", layout="wide")
st.title("📋 Malla de Asistencia Diaria - Dinámica")

tab_asistencia, tab_dashboard = st.tabs(["⚡ Registrar Asistencia", "📊 Dashboard y Reportes"])

with tab_asistencia:
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        st.success(f"Sistema ABIERTO. Hora actual: {ahora.strftime('%H:%M')}")
        
        col_sel, col_info = st.columns([1, 2])
        with col_sel:
            equipo_sel = st.selectbox("Selecciona tu Equipo:", list(EQUIPOS.keys()))
        
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        st.write(f"### 👥 Gestionando: {equipo_sel}")
        st.info("💡 Tip: Usa la última fila vacía o el botón '+' para agregar personas nuevas hoy.")
        
        # Cargar lista base del equipo
        datos_equipo = []
        for persona in EQUIPOS[equipo_sel]:
            datos_equipo.append({
                "Fecha": fecha_hoy,
                "Equipo": equipo_sel,
                "Nombre": persona,
                "Estado": "Presente", 
                "Observacion": ""
            })
        
        df_input = pd.DataFrame(datos_equipo)
        
        # --- CAMBIO CLAVE: num_rows="dynamic" ---
        df_editado = st.data_editor(
            df_input,
            column_config={
                "Fecha": st.column_config.Column(disabled=True), # Bloqueamos fecha para que no la cambien por error
                "Equipo": st.column_config.Column(disabled=True),
                "Nombre": st.column_config.TextColumn("Nombre (Escribe aquí)", required=True),
                "Estado": st.column_config.SelectboxColumn(
                    "Estado",
                    options=["Presente", "Ausente", "Tarde", "Licencia", "Vacaciones"],
                    required=True
                ),
                "Observacion": st.column_config.TextColumn("Observación")
            },
            hide_index=True,
            num_rows="dynamic", # ¡ESTO PERMITE AGREGAR FILAS!
            use_container_width=True
        )
        
        if st.button("💾 Guardar Asistencia Completa"):
            # Aseguramos que las filas nuevas tengan la fecha y equipo correctos
            if not df_editado.empty:
                df_editado["Fecha"] = fecha_hoy
                df_editado["Equipo"] = equipo_sel
                
                guardar_asistencia(df_editado)
                st.toast(f"✅ Asistencia guardada correctamente con {len(df_editado)} registros.")
            else:
                st.warning("No hay datos para guardar.")
            
    else:
        st.error(f"⛔ Sistema CERRADO. Horario de gestión: {HORA_INICIO} a {HORA_FIN}.")

with tab_dashboard:
    st.header("📊 Reporte General")
    df = cargar_datos()
    
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_equipo = st.multiselect("Filtrar Equipo:", df["Equipo"].unique(), default=df["Equipo"].unique())
        with col2:
            filtro_estado = st.multiselect("Filtrar Estado:", df["Estado"].unique(), default=df["Estado"].unique())
        with col3:
            fechas_disp = sorted(df["Fecha"].unique())
            filtro_fecha = st.selectbox("Filtrar Fecha:", fechas_disp, index=len(fechas_disp)-1)
        
        df_filtrado = df[
            df["Equipo"].isin(filtro_equipo) & 
            df["Estado"].isin(filtro_estado) & 
            (df["Fecha"] == filtro_fecha)
        ]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Personas", len(df_filtrado))
        m2.metric("✅ Presentes", len(df_filtrado[df_filtrado['Estado'] == 'Presente']))
        m3.metric("❌ Ausentes", len(df_filtrado[df_filtrado['Estado'] == 'Ausente']), delta_color="inverse")
        
        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.info("Aún no hay datos.")
