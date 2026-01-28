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
    """Esta función reescribe todo el archivo de asistencia (usada para borrar)"""
    # Nos aseguramos de guardar solo las columnas originales, sin la columna 'Borrar'
    cols_reales = ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]
    # Filtramos por si acaso el DF trae columnas extra
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

tab_personal, tab_asistencia, tab_reporte = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "📊 HISTÓRICO"])

# ==========================================
# PESTAÑA 1: GESTIÓN
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
# PESTAÑA 2: ASISTENCIA
# ==========================================
with tab_asistencia:
    st.header("Registro Diario")
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        equipo_asist = st.selectbox("Selecciona Equipo:", list(EQUIPOS_INICIALES.keys()), key="sel_asist")
        df_db = cargar_csv(ARCHIVO_EMPLEADOS)
        df_personal_base = df_db[df_db['Equipo'] == equipo_asist]
        
        if not df_personal_base.empty:
            df_input = df_personal_base[['Nombre', 'Cedula']].copy()
            df_input['Estado'] = "Asiste"
            df_input['Observacion'] = ""
            df_input['Soporte'] = None
            
            st.write(f"Gestionando: **{equipo_asist}**")
            
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
                st.warning("⚠️ ¡Atención! Se han detectado novedades. Por favor carga los soportes:")
                with st.expander("📂 ZONA DE CARGA DE SOPORTES", expanded=True):
                    cols = st.columns(3)
                    i = 0
                    for index, row in novedades.iterrows():
                        nombre = row['Nombre']
                        estado = row['Estado']
                        with cols[i % 3]:
                            st.markdown(f"**{nombre}** ({estado})")
                            file = st.file_uploader(f"Subir imagen para {nombre}", type=["png", "jpg", "jpeg"], key=f"file_{nombre}")
                            if file:
                                archivos_subidos[nombre] = file
                        i += 1

            if st.button("💾 GUARDAR ASISTENCIA Y SOPORTES", type="primary"):
                df_guardar = df_asistencia_editada.copy()
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                df_guardar['Fecha'] = fecha_hoy
                df_guardar['Equipo'] = equipo_asist
                
                lista_rutas = []
                for index, row in df_guardar.iterrows():
                    nombre = row['Nombre']
                    ruta = ""
                    if nombre in archivos_subidos:
                        ruta = guardar_imagen(archivos_subidos[nombre], nombre, fecha_hoy)
                    lista_rutas.append(ruta)
                
                df_guardar['Soporte'] = lista_rutas
                
                cols_finales = ['Fecha', 'Equipo', 'Nombre', 'Cedula', 'Estado', 'Observacion', 'Soporte']
                guardar_asistencia(df_guardar[cols_finales])
                st.success("✅ Asistencia guardada correctamente.")
                
    else:
        st.error("⛔ Sistema Cerrado.")

# ==========================================
# PESTAÑA 3: HISTÓRICO (CON MODO CORRECCIÓN)
# ==========================================
with tab_reporte:
    st.header("Histórico y Correcciones")
    df_hist = cargar_csv(ARCHIVO_ASISTENCIA)
    
    if not df_hist.empty:
        # --- SWITCH PARA MODO EDICIÓN ---
        modo_correccion = st.toggle("🛠️ ACTIVAR MODO CORRECCIÓN (Borrar filas individuales)")
        
        if modo_correccion:
            st.warning("⚠️ ESTÁS EN MODO CORRECCIÓN. Selecciona la casilla 'Borrar' de las filas que quieras eliminar y dale al botón rojo.")
            
            # Preparamos el DF para edición: Agregamos columna checkbox
            df_to_edit = df_hist.copy()
            df_to_edit.insert(0, "Borrar", False) # Columna checkbox al inicio
            
            # Editor FULL (Sin filtros para evitar errores de guardado parcial)
            edited_df = st.data_editor(
                df_to_edit,
                column_config={
                    "Borrar": st.column_config.CheckboxColumn("¿Borrar?", help="Marca para eliminar", default=False),
                    "Fecha": st.column_config.Column(disabled=True),
                    "Equipo": st.column_config.Column(disabled=True),
                    "Nombre": st.column_config.Column(disabled=True),
                    "Estado": st.column_config.Column(disabled=True),
                },
                disabled=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"], # Todo bloqueado menos el checkbox
                hide_index=True,
                use_container_width=True,
                key="editor_correccion"
            )
            
            # Lógica de borrado
            filas_a_borrar = edited_df[edited_df["Borrar"] == True]
            
            if not filas_a_borrar.empty:
                st.error(f"Has marcado {len(filas_a_borrar)} registro(s) para eliminar.")
                if st.button("🗑️ ELIMINAR REGISTROS MARCADOS PERMANENTEMENTE", type="primary"):
                    # Filtramos el DF original quedándonos solo con los que NO tienen 'Borrar' == True
                    df_final = edited_df[edited_df["Borrar"] == False]
                    
                    # Guardamos sobrescribiendo el archivo
                    sobrescribir_asistencia_completa(df_final)
                    st.success("✅ Registros eliminados correctamente.")
                    st.rerun()
            
        else:
            # --- MODO VISUALIZACIÓN (Seguro, con filtros) ---
            col1, col2 = st.columns(2)
            with col1:
                filtro_equipo = st.multiselect("Filtrar Equipo:", df_hist["Equipo"].unique())
            with col2:
                filtro_fecha = st.multiselect("Filtrar Fecha:", df_hist["Fecha"].unique())
                
            df_show = df_hist.copy()
            if filtro_equipo:
                df_show = df_show[df_show["Equipo"].isin(filtro_equipo)]
            if filtro_fecha:
                df_show = df_show[df_show["Fecha"].isin(filtro_fecha)]
                
            st.dataframe(df_show, use_container_width=True)
            
            # Visualizador de Soportes
            st.divider()
            df_con_soporte = df_show[df_show['Soporte'].notna() & (df_show['Soporte'].str.len() > 5)]
            if not df_con_soporte.empty:
                st.subheader("🔍 Visualizador de Soportes")
                persona_ver = st.selectbox("Selecciona registro para ver soporte:", 
                                         df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'] + " (" + df_con_soporte['Estado'] + ")")
                if persona_ver:
                    datos_row = df_con_soporte[ (df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'] + " (" + df_con_soporte['Estado'] + ")") == persona_ver ].iloc[0]
                    ruta_img = datos_row['Soporte']
                    if os.path.exists(ruta_img):
                        st.image(Image.open(ruta_img), caption=f"Soporte de {datos_row['Nombre']}", width=400)
    else:
        st.info("No hay datos históricos.")

    # Zona de Peligro (Reset Total)
    st.divider()
    with st.expander("☢️ ZONA DE PELIGRO (Reset Total)"):
        st.warning("Esto borra TODO el historial.")
        if st.button("🔴 BORRAR TODO", type="primary"):
            borrar_historial_completo()
            st.rerun()
