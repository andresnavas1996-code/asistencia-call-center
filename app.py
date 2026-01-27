import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- 1. CONFIGURACIÓN (Aquí agregas/quitas personas fácilmente) ---
EQUIPOS = {
    "Ventas": ["Ana", "Carlos", "Beatriz", "David"],
    "Soporte": ["Elena", "Fernando", "Gabriela"],
    "Logística": ["Hugo", "Inés", "Javier"]
}

# Configuración del horario de edición (Ej: de 8:00 AM a 9:00 AM)
HORA_INICIO = time(8, 0)
HORA_FIN = time(23, 59) # Puse un rango amplio para que lo pruebes, ajústalo a 1 hora (ej: 9, 0)
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
st.title("📋 Malla de Asistencia Diaria")

# Pestañas para separar la "Toma de lista" del "Dashboard"
tab_asistencia, tab_dashboard = st.tabs(["⚡ Registrar Asistencia", "📊 Dashboard y Reportes"])

with tab_asistencia:
    # Lógica de restricción de tiempo
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        st.success(f"Sistema ABIERTO (Hora actual: {ahora.strftime('%H:%M')}). Tienes hasta las {HORA_FIN} para gestionar.")
        
        # Selector de equipo
        equipo_sel = st.selectbox("Selecciona el Equipo a gestionar:", list(EQUIPOS.keys()))
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        st.write(f"### Asistencia: {equipo_sel} - Fecha: {fecha_hoy}")
        
        # Crear la "Malla" para llenar
        datos_equipo = []
        for persona in EQUIPOS[equipo_sel]:
            datos_equipo.append({
                "Fecha": fecha_hoy,
                "Equipo": equipo_sel,
                "Nombre": persona,
                "Estado": "Presente", # Valor por defecto
                "Observacion": ""
            })
        
        df_input = pd.DataFrame(datos_equipo)
        
        # Editor interactivo (La Malla)
        df_editado = st.data_editor(
            df_input,
            column_config={
                "Estado": st.column_config.SelectboxColumn(
                    "Estado",
                    options=["Presente", "Ausente", "Tarde", "Licencia"],
                    required=True
                )
            },
            hide_index=True,
            num_rows="fixed"
        )
        
        if st.button("Guardar Asistencia del Equipo"):
            guardar_asistencia(df_editado)
            st.toast(f"✅ Asistencia de {equipo_sel} guardada con éxito!")
            
    else:
        st.error(f"⛔ El sistema está CERRADO. El horario de gestión es de {HORA_INICIO} a {HORA_FIN}.")
        st.info("Contacta al administrador si necesitas realizar un cambio fuera de horario.")

with tab_dashboard:
    st.header("Visualización de Datos")
    df = cargar_datos()
    
    if not df.empty:
        # Filtros básicos
        col1, col2 = st.columns(2)
        with col1:
            filtro_equipo = st.multiselect("Filtrar por Equipo:", df["Equipo"].unique(), default=df["Equipo"].unique())
        with col2:
            filtro_estado = st.multiselect("Filtrar por Estado:", df["Estado"].unique(), default=df["Estado"].unique())
        
        df_filtrado = df[df["Equipo"].isin(filtro_equipo) & df["Estado"].isin(filtro_estado)]
        
        # Métricas rápidas
        t_asistencias = len(df_filtrado[df_filtrado['Estado'] == 'Presente'])
        t_ausencias = len(df_filtrado[df_filtrado['Estado'] == 'Ausente'])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Registros", len(df_filtrado))
        m2.metric("Asistencias", t_asistencias)
        m3.metric("Ausencias", t_ausencias, delta_color="inverse")
        
        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.info("Aún no hay datos registrados.")
