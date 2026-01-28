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

# 4 PESTAÑAS: GESTIÓN, ASISTENCIA (COLA DE TRABAJO), VISUAL (SOLO LECTURA), ADMIN (EDITAR)
tab_personal, tab_asistencia, tab_visual, tab_admin = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "👁️ VISUALIZAR HISTÓRICO", "🔐 ADMINISTRAR (CLAVE)"])

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
# PESTAÑA 2: ASISTENCIA (MODO COLA DE TRABAJO)
# ==========================================
with tab_asistencia:
    st.header("Registro Diario (Pendientes)")
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        equipo_asist = st.selectbox("Selecciona Equipo:", list(EQUIPOS_INICIALES.keys()), key="sel_asist")
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        # 1. Cargar empleados del equipo
        df_db = cargar_csv(ARCHIVO_EMPLEADOS)
        df_personal_base = df_db[df_db['Equipo'] == equipo_asist]
        
        # 2. Cargar historial de HOY para saber quién ya fue gestionado
        df_historial = cargar_csv(ARCHIVO_ASISTENCIA)
        ya_registrados = []
        if not df_historial.empty:
            ya_registrados = df_historial[
                (df_historial['Fecha'] == fecha_hoy) & 
                (df_historial['Equipo'] == equipo_asist)
            ]['Nombre'].tolist()
        
        # 3. Filtrar: Solo mostramos los que NO están en "ya_registrados"
        df_pendientes = df_personal_base[~df_personal_base['Nombre'].isin(ya_registrados)]
        
        if not df_pendientes.empty:
            # Preparamos la tabla
            df_input = df_pendientes[['Nombre', 'Cedula']].copy()
            df_input['Estado'] = None # EMPIEZA VACÍO
            df_input['Observacion'] = ""
            df_input['Soporte'] = None
            
            st.info(f"📅 Fecha: {fecha_hoy} | ⏳ Pendientes por gestionar: {len(df_input)}")
            
            # EDITOR
            df_asistencia_editada = st.data_editor(
                df_input,
                column_config={
                    "Nombre": st.column_config.Column(disabled=True),
                    "Cedula": st.column_config.Column(disabled=True),
                    "Estado": st.column_config.SelectboxColumn(
                        "Estado (Seleccionar)", 
                        options=["Asiste", "Ausente", "Llegada tarde", "Incapacidad", "Vacaciones"],
                        required=True # Obliga a elegir algo si quieres guardar esa fila
                    ),
                    "Observacion": st.column_config.TextColumn("Observación"),
                    "Soporte": st.column_config.Column(disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                key="editor_asistencia_dia"
            )
            
            # Detectar novedades en lo que se está editando ahora
            novedades = df_asistencia_editada[df_asistencia_editada['Estado'].isin(["Llegada tarde", "Incapacidad"])]
            archivos_subidos = {}
            
            if not novedades.empty:
                st.warning("⚠️ Carga los soportes para las novedades seleccionadas:")
                with st.expander("📂 ZONA DE CARGA DE SOPORTES", expanded=True):
                    cols = st.columns(3)
                    i = 0
                    for index, row in novedades.iterrows():
                        nombre = row['Nombre']
                        estado = row['Estado']
                        with cols[i % 3]:
                            st.markdown(f"**{nombre}** ({estado})")
                            file = st.file_uploader(f"Adjunto:", type=["png", "jpg", "jpeg"], key=f"file_{nombre}")
                            if file:
                                archivos_subidos[nombre] = file
                        i += 1

            # BOTÓN DE GUARDADO
            if st.button("💾 GUARDAR REGISTROS SELECCIONADOS", type="primary"):
                # Filtramos: Solo guardamos las filas donde se haya elegido un Estado (No guardamos los None)
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
                    
                    st.success(f"✅ Se guardaron {len(df_final)} registros. ¡Esas personas desaparecerán de la lista!")
                    st.rerun() # ESTO ES LO QUE HACE QUE DESAPAREZCAN AL INSTANTE
                else:
                    st.warning("⚠️ No has seleccionado ningún estado para guardar.")
        else:
            st.success(f"🎉 ¡Todo listo! No hay pendientes en {equipo_asist} para hoy.")
            st.balloons()
                
    else:
        st.error("⛔ Sistema Cerrado.")

# ==========================================
# PESTAÑA 3: VISUALIZAR HISTÓRICO (SOLO LECTURA)
# ==========================================
with tab_visual:
    st.header("👁️ Visualización de Registros (Solo Lectura)")
    df_hist = cargar_csv(ARCHIVO_ASISTENCIA)
    
    if not df_hist.empty:
        col1, col2 = st.columns(2)
        with col1:
            filtro_equipo = st.multiselect("Filtrar Equipo:", df_hist["Equipo"].unique(), key="viz_equipo")
        with col2:
            filtro_fecha = st.multiselect("Filtrar Fecha:", df_hist["Fecha"].unique(), key="viz_fecha")
            
        df_show = df_hist.copy()
        if filtro_equipo:
            df_show = df_show[df_show["Equipo"].isin(filtro_equipo)]
        if filtro_fecha:
            df_show = df_show[df_show["Fecha"].isin(filtro_fecha)]
            
        st.dataframe(df_show, use_container_width=True)
        st.caption(f"Total registros encontrados: {len(df_show)}")
        
        st.divider()
        df_con_soporte = df_show[df_show['Soporte'].notna() & (df_show['Soporte'].str.len() > 5)]
        if not df_con_soporte.empty:
            st.subheader("🔍 Visualizador de Soportes")
            persona_ver = st.selectbox("Selecciona registro:", 
                                     df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'] + " (" + df_con_soporte['Estado'] + ")", key="viz_soporte")
            if persona_ver:
                datos_row = df_con_soporte[ (df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'] + " (" + df_con_soporte['Estado'] + ")") == persona_ver ].iloc[0]
                ruta_img = datos_row['Soporte']
                if os.path.exists(ruta_img):
                    st.image(Image.open(ruta_img), caption=f"Soporte de {datos_row['Nombre']}", width=400)
    else:
        st.info("No hay datos históricos.")

# ==========================================
# PESTAÑA 4: ADMINISTRAR (CLAVE 1234)
# ==========================================
with tab_admin:
    st.header("🔐 Administración y Correcciones")
    
    clave_ingresada = st.text_input("Ingrese la clave de administrador:", type="password")
    
    if clave_ingresada == "1234":
        st.success("Acceso concedido.")
        
        df_hist = cargar_csv(ARCHIVO_ASISTENCIA)
        if not df_hist.empty:
            st.warning("⚠️ MODO EDICIÓN ACTIVO: Puedes cambiar datos o borrar filas.")
            
            df_to_edit = df_hist.copy()
            df_to_edit.insert(0, "Borrar", False) 
            
            edited_df = st.data_editor(
                df_to_edit,
                column_config={
                    "Borrar": st.column_config.CheckboxColumn("¿Borrar?", default=False),
                    "Fecha": st.column_config.Column(disabled=True),
                    "Equipo": st.column_config.Column(disabled=True),
                    "Nombre": st.column_config.TextColumn("Nombre", required=True),
                    "Cedula": st.column_config.TextColumn("Cédula"),
                    "Estado": st.column_config.SelectboxColumn("Estado", options=["Asiste", "Ausente", "Llegada tarde", "Incapacidad", "Vacaciones"], required=True),
                    "Observacion": st.column_config.TextColumn("Observación"),
                    "Soporte": st.column_config.Column(disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                key="editor_admin_total"
            )
            
            if st.button("💾 GUARDAR CAMBIOS Y BORRADOS", type="primary"):
                df_final = edited_df[edited_df["Borrar"] == False]
                sobrescribir_asistencia_completa(df_final)
                
                borrados = len(edited_df) - len(df_final)
                if borrados > 0:
                    st.success(f"✅ Se eliminaron {borrados} registros. (Volverán a aparecer en la lista de pendientes si eran de hoy).")
                else:
                    st.success("✅ Cambios guardados.")
                st.rerun()

            st.divider()
            with st.expander("☢️ ZONA DE PELIGRO (Reset Total)"):
                st.warning("Esto borra TODO el historial.")
                if st.button("🔴 BORRAR TODO", type="primary"):
                    borrar_historial_completo()
                    st.rerun()
        else:
            st.info("No hay datos históricos para administrar.")
            
    elif clave_ingresada:
        st.error("Clave incorrecta.")
