import streamlit as st
import pandas as pd
from datetime import datetime, time
import os
from PIL import Image

# --- 1. CONFIGURACIÓN ---
HORA_INICIO = time(0, 0)
HORA_FIN = time(23, 59)
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'
CARPETA_SOPORTES = 'soportes_img' 

# Equipos iniciales
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
    if not os.path.exists(CARPETA_SOPORTES):
        os.makedirs(CARPETA_SOPORTES)
        
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        datos_lista = []
        for equipo, nombres in EQUIPOS_INICIALES.items():
            for nombre in nombres:
                datos_lista.append({"Equipo": equipo, "Nombre": nombre, "Cedula": ""})
        pd.DataFrame(datos_lista).to_csv(ARCHIVO_EMPLEADOS, index=False)
    
    if not os.path.exists(ARCHIVO_ASISTENCIA):
        pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]).to_csv(ARCHIVO_ASISTENCIA, index=False)
    else:
        df_temp = pd.read_csv(ARCHIVO_ASISTENCIA)
        if "Soporte" not in df_temp.columns:
            df_temp["Soporte"] = None
            df_temp.to_csv(ARCHIVO_ASISTENCIA, index=False)

def cargar_csv(archivo):
    asegurar_archivos()
    try:
        return pd.read_csv(archivo, dtype=str, keep_default_na=False)
    except:
        return pd.DataFrame()

def guardar_personal(df_nuevo, equipo_actual):
    df_todos = cargar_csv(ARCHIVO_EMPLEADOS)
    df_todos = df_todos[df_todos['Equipo'] != equipo_actual]
    df_nuevo['Equipo'] = equipo_actual
    df_final = pd.concat([df_todos, df_nuevo], ignore_index=True)
    df_final.to_csv(ARCHIVO_EMPLEADOS, index=False)

def guardar_asistencia(df_registro):
    df_historico = cargar_csv(ARCHIVO_ASISTENCIA)
    df_final = pd.concat([df_historico, df_registro], ignore_index=True)
    df_final.to_csv(ARCHIVO_ASISTENCIA, index=False)

def sobrescribir_asistencia_completa(df_completo):
    cols_reales = ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]
    df_final = df_completo[cols_reales]
    df_final.to_csv(ARCHIVO_ASISTENCIA, index=False)

def guardar_imagen(uploaded_file, nombre_persona, fecha):
    if uploaded_file is not None:
        ext = uploaded_file.name.split('.')[-1]
        nombre_archivo = f"{fecha}_{nombre_persona.replace(' ', '_')}.{ext}"
        ruta_completa = os.path.join(CARPETA_SOPORTES, nombre_archivo)
        with open(ruta_completa, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return ruta_completa
    return None

def borrar_historial_completo():
    pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]).to_csv(ARCHIVO_ASISTENCIA, index=False)

# --- 3. INTERFAZ ---
st.set_page_config(page_title="Gestión Asistencia", layout="wide")
st.title("📋 Sistema Integral de Asistencia")

asegurar_archivos()

# PESTAÑAS
tab_personal, tab_asistencia, tab_visual, tab_admin = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "📊 DASHBOARD HISTÓRICO", "🔐 ADMINISTRAR"])

# ==========================================
# PESTAÑA 1: GESTIÓN PERSONAL
# ==========================================
with tab_personal:
    st.header("Actualización de Base de Datos")
    equipo_gest = st.selectbox("Selecciona Equipo a Editar:", list(EQUIPOS_INICIALES.keys()), key="sel_gest")
    df_db = cargar_csv(ARCHIVO_EMPLEADOS)
    df_equipo = df_db[df_db['Equipo'] == equipo_gest][['Nombre', 'Cedula']]
    
    df_editado_personal = st.data_editor(
        df_equipo,
        column_config={"Nombre": st.column_config.TextColumn("Nombre", required=True), "Cedula": st.column_config.TextColumn("Cédula", required=True)},
        num_rows="dynamic",
        use_container_width=True,
        key="editor_personal"
    )
    
    if st.button("💾 ACTUALIZAR BASE DE DATOS", type="primary"):
        guardar_personal(df_editado_personal, equipo_gest)
        st.success(f"✅ Base de datos actualizada.")
        st.rerun()

# ==========================================
# PESTAÑA 2: ASISTENCIA (COLA DE TRABAJO)
# ==========================================
with tab_asistencia:
    st.header("Registro Diario (Pendientes)")
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        equipo_asist = st.selectbox("Selecciona Equipo:", list(EQUIPOS_INICIALES.keys()), key="sel_asist")
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        # Lógica de Cola: Empleados - Historial Hoy
        df_db = cargar_csv(ARCHIVO_EMPLEADOS)
        df_personal_base = df_db[df_db['Equipo'] == equipo_asist]
        
        df_historial = cargar_csv(ARCHIVO_ASISTENCIA)
        ya_registrados = []
        if not df_historial.empty:
            ya_registrados = df_historial[
                (df_historial['Fecha'] == fecha_hoy) & 
                (df_historial['Equipo'] == equipo_asist)
            ]['Nombre'].tolist()
        
        df_pendientes = df_personal_base[~df_personal_base['Nombre'].isin(ya_registrados)]
        
        if not df_pendientes.empty:
            df_input = df_pendientes[['Nombre', 'Cedula']].copy()
            df_input['Estado'] = None 
            df_input['Observacion'] = ""
            df_input['Soporte'] = None
            
            st.info(f"📅 Fecha: {fecha_hoy} | ⏳ Pendientes: {len(df_input)}")
            
            df_asistencia_editada = st.data_editor(
                df_input,
                column_config={
                    "Nombre": st.column_config.Column(disabled=True),
                    "Cedula": st.column_config.Column(disabled=True),
                    "Estado": st.column_config.SelectboxColumn("Estado", options=["Asiste", "Ausente", "Llegada tarde", "Incapacidad", "Vacaciones"], required=True),
                    "Observacion": st.column_config.TextColumn("Observación"),
                    "Soporte": st.column_config.Column(disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                key="editor_asistencia_dia"
            )
            
            novedades = df_asistencia_editada[df_asistencia_editada['Estado'].isin(["Llegada tarde", "Incapacidad"])]
            archivos_subidos = {}
            
            if not novedades.empty:
                st.warning("⚠️ Carga los soportes para las novedades:")
                with st.expander("📂 ZONA DE CARGA", expanded=True):
                    cols = st.columns(3)
                    i = 0
                    for index, row in novedades.iterrows():
                        nombre = row['Nombre']
                        with cols[i % 3]:
                            st.markdown(f"**{nombre}**")
                            file = st.file_uploader(f"Adjunto:", type=["png", "jpg", "jpeg"], key=f"file_{nombre}")
                            if file:
                                archivos_subidos[nombre] = file
                        i += 1

            if st.button("💾 GUARDAR SELECCIONADOS", type="primary"):
                df_a_guardar = df_asistencia_editada.dropna(subset=['Estado'])
                if not df_a_guardar.empty:
                    df_final = df_a_guardar.copy()
                    df_final['Fecha'] = fecha_hoy
                    df_final['Equipo'] = equipo_asist
                    
                    lista_rutas = []
                    for index, row in df_final.iterrows():
                        nombre = row['Nombre']
                        ruta = ""
                        if nombre in archivos_subidos:
                            ruta = guardar_imagen(archivos_subidos[nombre], nombre, fecha_hoy)
                        lista_rutas.append(ruta)
                    
                    df_final['Soporte'] = lista_rutas
                    cols_finales = ['Fecha', 'Equipo', 'Nombre', 'Cedula', 'Estado', 'Observacion', 'Soporte']
                    guardar_asistencia(df_final[cols_finales])
                    st.success(f"✅ {len(df_final)} registros guardados.")
                    st.rerun()
                else:
                    st.warning("Selecciona un estado para guardar.")
        else:
            st.success("🎉 Todo gestionado hoy.")
            st.balloons()
    else:
        st.error("⛔ Sistema Cerrado.")

# ==========================================
# PESTAÑA 3: DASHBOARD HISTÓRICO (MEJORADA)
# ==========================================
with tab_visual:
    st.header("📊 Dashboard de Gestión")
    df_hist = cargar_csv(ARCHIVO_ASISTENCIA)
    
    if not df_hist.empty:
        # --- FILTROS SUPERIORES ---
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                filtro_equipo = st.multiselect("Filtrar Equipo:", df_hist["Equipo"].unique(), key="viz_equipo")
            with col2:
                filtro_fecha = st.multiselect("Filtrar Fecha:", df_hist["Fecha"].unique(), key="viz_fecha")
        
        # Aplicar filtros
        df_show = df_hist.copy()
        if filtro_equipo:
            df_show = df_show[df_show["Equipo"].isin(filtro_equipo)]
        if filtro_fecha:
            df_show = df_show[df_show["Fecha"].isin(filtro_fecha)]
            
        # --- KPIs (INDICADORES) ---
        total_regs = len(df_show)
        if total_regs > 0:
            asistencias = len(df_show[df_show['Estado'] == 'Asiste'])
            tardanzas = len(df_show[df_show['Estado'] == 'Llegada tarde'])
            incapacidades = len(df_show[df_show['Estado'] == 'Incapacidad'])
            ausencias = len(df_show[df_show['Estado'] == 'Ausente'])
            
            porc_asistencia = (asistencias / total_regs) * 100
        else:
            asistencias, tardanzas, incapacidades, ausencias, porc_asistencia = 0, 0, 0, 0, 0

        st.subheader("Indicadores Clave")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Gestionados", total_regs)
        kpi2.metric("% Asistencia", f"{porc_asistencia:.1f}%")
        kpi3.metric("Llegadas Tarde", tardanzas, delta_color="inverse")
        kpi4.metric("Incapacidades/Ausencias", incapacidades + ausencias, delta_color="inverse")
        
        st.divider()

        # --- GRÁFICOS ---
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("Distribución por Estado")
            # Gráfico simple de barras contando estados
            if not df_show.empty:
                conteo_estados = df_show['Estado'].value_counts()
                st.bar_chart(conteo_estados, color="#4CAF50") # Verde genérico
            
        with col_graf2:
            st.subheader("Registros por Equipo")
            if not df_show.empty:
                conteo_equipos = df_show['Equipo'].value_counts()
                st.bar_chart(conteo_equipos, color="#2196F3") # Azul

        st.divider()

        # --- TABLA DETALLADA ---
        st.subheader("📋 Detalle de Registros")
        st.dataframe(df_show, use_container_width=True)
        
        # --- VISUALIZADOR DE SOPORTES ---
        st.subheader("🔍 Visualizador de Soportes")
        df_con_soporte = df_show[df_show['Soporte'].notna() & (df_show['Soporte'].str.len() > 5)]
        
        if not df_con_soporte.empty:
            persona_ver = st.selectbox("Selecciona registro para ver soporte:", 
                                     df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'] + " (" + df_con_soporte['Estado'] + ")", key="viz_soporte")
            if persona_ver:
                datos_row = df_con_soporte[ (df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'] + " (" + df_con_soporte['Estado'] + ")") == persona_ver ].iloc[0]
                ruta_img = datos_row['Soporte']
                if os.path.exists(ruta_img):
                    st.image(Image.open(ruta_img), caption=f"Soporte de {datos_row['Nombre']}", width=400)
                else:
                    st.error("Imagen no encontrada en el servidor.")
        else:
            st.info("No hay soportes para mostrar en los filtros seleccionados.")
            
    else:
        st.info("No hay datos históricos para mostrar aún.")

# ==========================================
# PESTAÑA 4: ADMIN
# ==========================================
with tab_admin:
    st.header("🔐 Administración")
    clave_ingresada = st.text_input("Clave:", type="password")
    
    if clave_ingresada == "1234":
        st.success("Acceso Admin Activo")
        df_hist = cargar_csv(ARCHIVO_ASISTENCIA)
        if not df_hist.empty:
            df_to_edit = df_hist.copy()
            df_to_edit.insert(0, "Borrar", False) 
            
            edited_df = st.data_editor(
                df_to_edit,
                column_config={
                    "Borrar": st.column_config.CheckboxColumn("¿Borrar?", default=False),
                    "Fecha": st.column_config.Column(disabled=True),
                    "Equipo": st.column_config.Column(disabled=True),
                    "Nombre": st.column_config.TextColumn("Nombre", required=True),
                    "Estado": st.column_config.SelectboxColumn("Estado", options=["Asiste", "Ausente", "Llegada tarde", "Incapacidad", "Vacaciones"], required=True),
                    "Soporte": st.column_config.Column(disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                key="editor_admin_total"
            )
            
            if st.button("💾 APLICAR CAMBIOS", type="primary"):
                df_final = edited_df[edited_df["Borrar"] == False]
                sobrescribir_asistencia_completa(df_final)
                st.success("Cambios aplicados.")
                st.rerun()

            with st.expander("☢️ BORRAR TODO"):
                if st.button("🔴 CONFIRMAR BORRADO TOTAL", type="primary"):
                    borrar_historial_completo()
                    st.rerun()
