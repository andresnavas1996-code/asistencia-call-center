import streamlit as st
import pandas as pd
from datetime import datetime, time
import os
from PIL import Image

# --- 1. CONFIGURACIÓN Y CLAVES ---
HORA_INICIO = time(0, 0)
HORA_FIN = time(23, 59)
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'
CARPETA_SOPORTES = 'soportes_img' 

# LISTA DE EQUIPOS
EQUIPOS_LISTA = [
    "Callcenter Bucaramanga",      # Clave: 1111
    "Callcenter Medellin",         # Clave: 2
    "Callcenter Bogota",           # Clave: 3
    "Servicio al cliente",         # Clave: 4
    "CallcenterMayoreo Medellin",  # Clave: 5
    "Campo 6",                     # Clave: 6
    "Campo 7",                     # Clave: 7
    "Campo 8",                     # Clave: 8
    "Campo 9",                     # Clave: 9
    "Campo 10",                    # Clave: 10
    "Campo 11"                     # Clave: 11
]

# MAPEO DE CLAVES (Aquí puedes cambiarlas después)
# Formato: "CONTRASEÑA" : "NOMBRE EXACTO DEL EQUIPO"
USUARIOS = {
    "1111": "Callcenter Bucaramanga",
    "2": "Callcenter Medellin",
    "3": "Callcenter Bogota",
    "4": "Servicio al cliente",
    "5": "CallcenterMayoreo Medellin",
    "6": "Campo 6",
    "7": "Campo 7",
    "8": "Campo 8",
    "9": "Campo 9",
    "10": "Campo 10",
    "11": "Campo 11",
    "1234": "ADMIN" # Clave maestra
}

# --- 2. FUNCIONES ---

def asegurar_archivos():
    if not os.path.exists(CARPETA_SOPORTES):
        os.makedirs(CARPETA_SOPORTES)
        
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        datos_lista = []
        for equipo in EQUIPOS_LISTA:
            # Creamos datos semilla vacíos o con nombres genéricos si se desea
            pass 
        # Creamos el archivo vacío con cabeceras si no existe
        pd.DataFrame(columns=["Equipo", "Nombre", "Cedula"]).to_csv(ARCHIVO_EMPLEADOS, index=False)
    
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

# ESTADO DE SESIÓN (LOGIN)
if 'usuario' not in st.session_state:
    st.session_state['usuario'] = None

# --- PANTALLA DE LOGIN ---
if st.session_state['usuario'] is None:
    st.title("🔐 Ingreso al Sistema")
    st.markdown("Por favor ingrese la clave asignada a su equipo.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        password = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            if password in USUARIOS:
                st.session_state['usuario'] = USUARIOS[password]
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop() # Detiene la ejecución aquí si no está logueado

# --- APLICACIÓN PRINCIPAL (SOLO SI ESTÁ LOGUEADO) ---

usuario_actual = st.session_state['usuario']
es_admin = (usuario_actual == "ADMIN")

# Barra lateral con Info y Logout
with st.sidebar:
    st.write(f"Hola, **{usuario_actual}**")
    if st.button("Cerrar Sesión"):
        st.session_state['usuario'] = None
        st.rerun()

st.title(f"📋 Asistencia: {usuario_actual if not es_admin else 'Vista Global'}")

asegurar_archivos()

# Definir pestañas según el rol
if es_admin:
    tab_personal, tab_asistencia, tab_visual, tab_admin = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "📊 DASHBOARD GLOBAL", "🔐 ADMINISTRAR BD"])
else:
    # Los usuarios normales ven menos pestañas y sin la de Admin
    tab_personal, tab_asistencia, tab_visual = st.tabs(["👥 MI EQUIPO", "⚡ TOMAR ASISTENCIA", "📊 MI DASHBOARD"])

# ==========================================
# PESTAÑA 1: GESTIÓN PERSONAL (DB)
# ==========================================
with tab_personal:
    st.header("Base de Datos de Empleados")
    
    # LOGICA DE SEGURIDAD DE EQUIPO
    if es_admin:
        equipo_gest = st.selectbox("Selecciona Equipo a Editar:", EQUIPOS_LISTA, key="sel_gest")
    else:
        # Si no es admin, el equipo está fijo y bloqueado
        equipo_gest = usuario_actual
        st.info(f"Gestionando personal de: **{equipo_gest}**")

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
        
        # LOGICA DE SEGURIDAD DE EQUIPO
        if es_admin:
            equipo_asist = st.selectbox("Selecciona Equipo:", EQUIPOS_LISTA, key="sel_asist")
        else:
            equipo_asist = usuario_actual
            # No mostramos selectbox, solo el título
        
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        # Lógica de Cola
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
            
            st.info(f"📅 Fecha: {fecha_hoy} | ⏳ Pendientes por gestionar en {equipo_asist}: {len(df_input)}")
            
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
                st.warning("⚠️ Carga los soportes:")
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
            if not df_personal_base.empty:
                st.success(f"🎉 Todo el equipo {equipo_asist} ha sido gestionado hoy.")
                st.balloons()
            else:
                st.warning("Este equipo aún no tiene personal en la Base de Datos. Ve a la primera pestaña para agregar gente.")
    else:
        st.error("⛔ Sistema Cerrado.")

# ==========================================
# PESTAÑA 3: DASHBOARD (FILTRADO POR SEGURIDAD)
# ==========================================
with tab_visual:
    st.header("📊 Dashboard de Resultados")
    df_hist = cargar_csv(ARCHIVO_ASISTENCIA)
    
    if not df_hist.empty:
        # LOGICA DE SEGURIDAD
        if not es_admin:
            # Si es usuario normal, forzamos el filtro a SU equipo
            df_hist = df_hist[df_hist['Equipo'] == usuario_actual]
            
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                # Si es Admin, ve el selector. Si es usuario, ve un texto fijo.
                if es_admin:
                    filtro_equipo = st.multiselect("Filtrar Equipo:", df_hist["Equipo"].unique(), key="viz_equipo")
                else:
                    st.markdown(f"**Equipo:** {usuario_actual}")
                    filtro_equipo = [usuario_actual] # Preselección forzada invisible
                    
            with col2:
                filtro_fecha = st.multiselect("Filtrar Fecha:", df_hist["Fecha"].unique(), key="viz_fecha")
        
        df_show = df_hist.copy()
        if es_admin and filtro_equipo:
            df_show = df_show[df_show["Equipo"].isin(filtro_equipo)]
        if filtro_fecha:
            df_show = df_show[df_show["Fecha"].isin(filtro_fecha)]
            
        # KPIs
        total_regs = len(df_show)
        if total_regs > 0:
            asistencias = len(df_show[df_show['Estado'] == 'Asiste'])
            tardanzas = len(df_show[df_show['Estado'] == 'Llegada tarde'])
            incapacidades = len(df_show[df_show['Estado'] == 'Incapacidad'])
            ausencias = len(df_show[df_show['Estado'] == 'Ausente'])
            porc_asistencia = (asistencias / total_regs) * 100
        else:
            asistencias, tardanzas, incapacidades, ausencias, porc_asistencia = 0, 0, 0, 0, 0

        st.subheader("Indicadores")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Gestionados", total_regs)
        kpi2.metric("% Asistencia", f"{porc_asistencia:.1f}%")
        kpi3.metric("Llegadas Tarde", tardanzas, delta_color="inverse")
        kpi4.metric("Incapacidades/Ausencias", incapacidades + ausencias, delta_color="inverse")
        
        st.divider()

        # GRÁFICOS
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("Estados")
            if not df_show.empty:
                st.bar_chart(df_show['Estado'].value_counts(), color="#4CAF50")
            
        with col_graf2:
            if es_admin:
                st.subheader("Comparativa por Equipos")
                if not df_show.empty:
                    st.bar_chart(df_show['Equipo'].value_counts(), color="#2196F3")
            else:
                st.info("Vista de equipo único.")

        st.divider()
        st.subheader("📋 Detalle")
        st.dataframe(df_show, use_container_width=True)
        
        st.subheader("🔍 Soportes")
        df_con_soporte = df_show[df_show['Soporte'].notna() & (df_show['Soporte'].str.len() > 5)]
        
        if not df_con_soporte.empty:
            persona_ver = st.selectbox("Ver soporte de:", 
                                     df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'] + " (" + df_con_soporte['Estado'] + ")", key="viz_soporte")
            if persona_ver:
                datos_row = df_con_soporte[ (df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'] + " (" + df_con_soporte['Estado'] + ")") == persona_ver ].iloc[0]
                ruta_img = datos_row['Soporte']
                if os.path.exists(ruta_img):
                    st.image(Image.open(ruta_img), caption=f"Soporte", width=400)
    else:
        st.info("No hay datos históricos.")

# ==========================================
# PESTAÑA 4: ADMIN (SOLO VISIBLE PARA ADMIN)
# ==========================================
if es_admin:
    with tab_admin:
        st.header("🔐 Administración Global")
        st.info("Como Administrador (1234), tienes permisos totales para corregir errores.")
        
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
            
            if st.button("💾 APLICAR CORRECCIONES", type="primary"):
                df_final = edited_df[edited_df["Borrar"] == False]
                sobrescribir_asistencia_completa(df_final)
                st.success("Cambios aplicados.")
                st.rerun()

            with st.expander("☢️ BORRAR TODO"):
                if st.button("🔴 CONFIRMAR BORRADO TOTAL", type="primary"):
                    borrar_historial_completo()
                    st.rerun()
