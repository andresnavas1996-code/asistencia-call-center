import streamlit as st
import pandas as pd
from datetime import datetime, time
import os
import pytz 
import json

# --- 1. CONFIGURACIÓN ---
# Configuración de página DEBE SER LA PRIMERA LÍNEA EJECUTABLE
st.set_page_config(page_title="Gestión Asistencia", layout="wide")

# Configuración de Zona Horaria
try:
    ZONA_HORARIA = pytz.timezone('America/Bogota')
except:
    ZONA_HORARIA = pytz.utc # Fallback por si falla la librería

HORA_INICIO_DEFAULT = time(0, 0)
HORA_FIN_DEFAULT = time(23, 59)

# Archivos
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'
ARCHIVO_PASSWORDS = 'config_passwords_v3.json' # Cambiamos nombre para forzar uno limpio
CARPETA_SOPORTES = 'soportes_img' 

# --- 2. FUNCIONES ROBUSTAS ---

def obtener_hora_colombia():
    return datetime.now(ZONA_HORARIA)

def reiniciar_configuracion_default():
    """Restaura la configuración si el archivo se daña."""
    defaults = {
        "ADMIN": {"password": "1234", "inicio": "00:00", "fin": "23:59"},
        "Callcenter Bucaramanga": {"password": "1", "inicio": "06:00", "fin": "14:00"},
        "Callcenter Medellin": {"password": "2", "inicio": "08:00", "fin": "17:00"},
        "Callcenter Bogota": {"password": "3", "inicio": "00:00", "fin": "23:59"},
        "Servicio al cliente": {"password": "4", "inicio": "00:00", "fin": "23:59"}
    }
    with open(ARCHIVO_PASSWORDS, 'w') as f:
        json.dump(defaults, f)
    return defaults

def cargar_configuracion():
    """Carga configuración con protección anti-errores."""
    if not os.path.exists(ARCHIVO_PASSWORDS):
        return reiniciar_configuracion_default()
    
    try:
        with open(ARCHIVO_PASSWORDS, 'r') as f:
            data = json.load(f)
            # Validación rápida: si está vacío o mal formado, reinicia
            if not data or not isinstance(data, dict):
                return reiniciar_configuracion_default()
            
            # Migración de datos viejos (string -> dict)
            for k, v in data.items():
                if isinstance(v, str):
                    data[k] = {"password": v, "inicio": "00:00", "fin": "23:59"}
            return data
    except:
        # Si hay error de lectura (JSON corrupto), reiniciamos para evitar bucle
        return reiniciar_configuracion_default()

def guardar_configuracion(diccionario_nuevo):
    # Asegurar que ADMIN existe
    if "ADMIN" not in diccionario_nuevo:
        diccionario_nuevo["ADMIN"] = {"password": "1234", "inicio": "00:00", "fin": "23:59"}
    
    with open(ARCHIVO_PASSWORDS, 'w') as f:
        json.dump(diccionario_nuevo, f)

def obtener_lista_equipos_dinamica():
    config = cargar_configuracion()
    lista = [k for k in config.keys() if k != "ADMIN"]
    return sorted(lista)

def verificar_horario(usuario):
    if usuario == "ADMIN": return True
    
    config = cargar_configuracion()
    if usuario in config:
        datos = config[usuario]
        inicio_str = datos.get("inicio", "00:00")
        fin_str = datos.get("fin", "23:59")
        try:
            h_inicio = datetime.strptime(inicio_str, "%H:%M").time()
            h_fin = datetime.strptime(fin_str, "%H:%M").time()
            hora_actual = obtener_hora_colombia().time()
            return h_inicio <= hora_actual <= h_fin
        except:
            return True 
    return True

def asegurar_archivos():
    if not os.path.exists(CARPETA_SOPORTES):
        os.makedirs(CARPETA_SOPORTES)
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        pd.DataFrame(columns=["Equipo", "Nombre", "Cedula"]).to_csv(ARCHIVO_EMPLEADOS, index=False)
    if not os.path.exists(ARCHIVO_ASISTENCIA):
        pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]).to_csv(ARCHIVO_ASISTENCIA, index=False)
    else:
        # Reparar columnas si faltan
        try:
            df_temp = pd.read_csv(ARCHIVO_ASISTENCIA)
            if "Soporte" not in df_temp.columns:
                df_temp["Soporte"] = None
                df_temp.to_csv(ARCHIVO_ASISTENCIA, index=False)
        except:
            pass # Si falla leyendo el CSV, no rompemos la app

def cargar_csv(archivo):
    asegurar_archivos()
    try:
        return pd.read_csv(archivo, dtype=str, keep_default_na=False)
    except:
        return pd.DataFrame()

def guardar_personal(df_nuevo, equipo_actual):
    df_todos = cargar_csv(ARCHIVO_EMPLEADOS)
    if not df_todos.empty and 'Equipo' in df_todos.columns:
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
    # Filtrar solo columnas existentes
    cols_validas = [c for c in cols_reales if c in df_completo.columns]
    df_final = df_completo[cols_validas]
    df_final.to_csv(ARCHIVO_ASISTENCIA, index=False)

def guardar_imagen(uploaded_file, nombre_persona, fecha):
    if uploaded_file is not None:
        try:
            ext = uploaded_file.name.split('.')[-1]
            nombre_archivo = f"{fecha}_{nombre_persona.replace(' ', '_')}.{ext}"
            ruta_completa = os.path.join(CARPETA_SOPORTES, nombre_archivo)
            with open(ruta_completa, "wb") as f:
                f.write(uploaded_file.getbuffer())
            return ruta_completa
        except:
            return None
    return None

def borrar_historial_completo():
    pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]).to_csv(ARCHIVO_ASISTENCIA, index=False)

# --- 3. LOGICA PRINCIPAL ---

if 'usuario' not in st.session_state:
    st.session_state['usuario'] = None

# Cargar configuración (esto crea el archivo si no existe)
config_db = cargar_configuracion()

# --- LOGIN ---
if st.session_state['usuario'] is None:
    st.title("🔐 Ingreso al Sistema")
    st.markdown("Por favor ingrese su clave de acceso.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        password_input = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            usuario_encontrado = None
            
            # 1. LLAVE MAESTRA OCULTA
            if password_input == "Admin26":
                usuario_encontrado = "ADMIN"
            else:
                # 2. BÚSQUEDA NORMAL
                for equipo, datos in config_db.items():
                    if isinstance(datos, dict) and password_input == datos.get('password'):
                        usuario_encontrado = equipo
                        break
                    elif isinstance(datos, str) and password_input == datos: # Fallback legacy
                        usuario_encontrado = equipo
                        break
            
            if usuario_encontrado:
                st.session_state['usuario'] = usuario_encontrado
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop() 

# --- APLICACIÓN ---
usuario_actual = st.session_state['usuario']
es_admin = (usuario_actual == "ADMIN")
equipos_disponibles = obtener_lista_equipos_dinamica()

# Verificar horario
en_horario = verificar_horario(usuario_actual)
config_usuario = config_db.get(usuario_actual, {})
horario_msg = f"{config_usuario.get('inicio', '00:00')} - {config_usuario.get('fin', '23:59')}" if isinstance(config_usuario, dict) else "24h"

with st.sidebar:
    st.write(f"Hola, **{usuario_actual}**")
    try:
        hora_co = obtener_hora_colombia().strftime("%H:%M")
        st.caption(f"🕒 Hora Colombia: {hora_co}")
    except:
        st.caption("Hora UTC")
        
    if not es_admin:
        st.caption(f"📅 Horario: {horario_msg}")
        if en_horario:
            st.success("✅ Acceso Permitido")
        else:
            st.error("⛔ Fuera de Horario")
            
    if st.button("Cerrar Sesión"):
        st.session_state['usuario'] = None
        st.rerun()

st.title(f"📋 Asistencia: {usuario_actual if not es_admin else 'Vista Global'}")

asegurar_archivos()

# --- ALERTA ADMIN (MEJORADA) ---
if es_admin:
    fecha_hoy_alert = obtener_hora_colombia().strftime("%Y-%m-%d")
    df_empleados_all = cargar_csv(ARCHIVO_EMPLEADOS)
    df_asistencia_all = cargar_csv(ARCHIVO_ASISTENCIA)
    
    if not df_asistencia_all.empty:
        df_asistencia_hoy = df_asistencia_all[df_asistencia_all['Fecha'] == fecha_hoy_alert]
    else:
        df_asistencia_hoy = pd.DataFrame()
    
    if not df_empleados_all.empty:
        df_empleados_all['Clave'] = df_empleados_all['Equipo'].astype(str) + df_empleados_all['Nombre'].astype(str)
        registrados_hoy = []
        if not df_asistencia_hoy.empty:
            df_asistencia_hoy['Clave'] = df_asistencia_hoy['Equipo'].astype(str) + df_asistencia_hoy['Nombre'].astype(str)
            registrados_hoy = df_asistencia_hoy['Clave'].tolist()
        
        df_faltantes = df_empleados_all[~df_empleados_all['Clave'].isin(registrados_hoy)].copy()
        
        if not df_faltantes.empty:
            total_pendientes = len(df_faltantes)
            st.error(f"⚠️ ALERTA: Faltan {total_pendientes} personas por reportar hoy.")
            
            if 'Equipo' in df_faltantes.columns:
                resumen_equipos = df_faltantes['Equipo'].value_counts().reset_index()
                resumen_equipos.columns = ['Equipo', 'Pendientes']
                
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.dataframe(resumen_equipos, hide_index=True, use_container_width=True)
                with c2:
                    with st.expander("🔍 Ver Detalle"):
                        st.dataframe(df_faltantes[['Equipo', 'Nombre']], hide_index=True, use_container_width=True)
            st.divider()

# --- PESTAÑAS ---
if es_admin:
    tab_personal, tab_asistencia, tab_visual, tab_admin = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "📊 DASHBOARD GLOBAL", "🔐 ADMINISTRAR"])
else:
    tab_personal, tab_asistencia, tab_visual = st.tabs(["👥 MI EQUIPO", "⚡ TOMAR ASISTENCIA", "📊 MI DASHBOARD"])

# 1. GESTIÓN
with tab_personal:
    if not es_admin and not en_horario:
        st.error("⛔ Fuera de horario.")
    else:
        st.header("Base de Datos")
        if es_admin:
            if equipos_disponibles:
                equipo_gest = st.selectbox("Equipo a Editar:", equipos_disponibles, key="sel_gest")
            else:
                st.warning("No hay equipos creados. Ve a 'ADMINISTRAR' para crear uno.")
                equipo_gest = None
        else:
            equipo_gest = usuario_actual
            st.info(f"Equipo: **{equipo_gest}**")

        if equipo_gest:
            df_db = cargar_csv(ARCHIVO_EMPLEADOS)
            if not df_db.empty and 'Equipo' in df_db.columns:
                df_equipo = df_db[df_db['Equipo'] == equipo_gest][['Nombre', 'Cedula']]
            else:
                df_equipo = pd.DataFrame(columns=['Nombre', 'Cedula'])
            
            df_editado_personal = st.data_editor(
                df_equipo,
                column_config={"Nombre": st.column_config.TextColumn("Nombre", required=True), "Cedula": st.column_config.TextColumn("Cédula", required=True)},
                num_rows="dynamic",
                use_container_width=True,
                key="editor_personal"
            )
            
            if st.button("💾 ACTUALIZAR BASE DE DATOS", type="primary"):
                guardar_personal(df_editado_personal, equipo_gest)
                st.success(f"✅ Guardado.")
                st.rerun()

# 2. ASISTENCIA
with tab_asistencia:
    if not es_admin and not en_horario:
        st.error("⛔ Fuera de horario.")
    else:
        st.header("Registro Diario")
        fecha_hoy = obtener_hora_colombia().strftime("%Y-%m-%d")
        
        if es_admin:
            if equipos_disponibles:
                equipo_asist = st.selectbox("Selecciona Equipo:", equipos_disponibles, key="sel_asist")
            else:
                equipo_asist = None
        else:
            equipo_asist = usuario_actual
        
        if equipo_asist:
            df_db = cargar_csv(ARCHIVO_EMPLEADOS)
            if not df_db.empty and 'Equipo' in df_db.columns:
                df_personal_base = df_db[df_db['Equipo'] == equipo_asist]
            else:
                df_personal_base = pd.DataFrame()
            
            df_historial = cargar_csv(ARCHIVO_ASISTENCIA)
            ya_registrados = []
            if not df_historial.empty and 'Fecha' in df_historial.columns:
                ya_registrados = df_historial[
                    (df_historial['Fecha'] == fecha_hoy) & 
                    (df_historial['Equipo'] == equipo_asist)
                ]['Nombre'].tolist()
            
            if not df_personal_base.empty:
                df_pendientes = df_personal_base[~df_personal_base['Nombre'].isin(ya_registrados)]
            else:
                df_pendientes = pd.DataFrame()
            
            if not df_pendientes.empty:
                df_input = df_pendientes[['Nombre', 'Cedula']].copy()
                df_input['Estado'] = None 
                df_input['Observacion'] = ""
                df_input['Soporte'] = None
                
                st.info(f"Pendientes: {len(df_input)}")
                
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
                    st.warning("⚠️ Carga soportes:")
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
                        st.success(f"✅ Guardado.")
                        st.rerun()
                    else:
                        st.warning("Selecciona un estado.")
            else:
                if not df_personal_base.empty:
                    st.success(f"🎉 Al día.")
                else:
                    st.warning("Sin personal.")

# 3. DASHBOARD
with tab_visual:
    st.header("📊 Dashboard")
    df_hist = cargar_csv(ARCHIVO_ASISTENCIA)
    
    if not df_hist.empty:
        if not es_admin:
            df_hist = df_hist[df_hist['Equipo'] == usuario_actual]
            
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                if es_admin:
                    filtro_equipo = st.multiselect("Filtrar Equipo:", df_hist["Equipo"].unique(), key="viz_equipo")
                else:
                    st.markdown(f"**Equipo:** {usuario_actual}")
                    filtro_equipo = [usuario_actual]
            with col2:
                filtro_fecha = st.multiselect("Filtrar Fecha:", df_hist["Fecha"].unique(), key="viz_fecha")
        
        df_show = df_hist.copy()
        if es_admin and filtro_equipo:
            df_show = df_show[df_show["Equipo"].isin(filtro_equipo)]
        if filtro_fecha:
            df_show = df_show[df_show["Fecha"].isin(filtro_fecha)]
            
        st.dataframe(df_show, use_container_width=True)
        
        # Visor Soportes
        if 'Soporte' in df_show.columns:
            df_con_soporte = df_show[df_show['Soporte'].notna() & (df_show['Soporte'].str.len() > 5)]
            if not df_con_soporte.empty:
                st.subheader("🔍 Soportes")
                persona_ver = st.selectbox("Ver soporte:", 
                                         df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'], key="viz_soporte")
                if persona_ver:
                    datos_row = df_con_soporte[ (df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha']) == persona_ver ].iloc[0]
                    try:
                        st.image(Image.open(datos_row['Soporte']), width=400)
                    except:
                        st.error("Imagen no encontrada")
    else:
        st.info("No hay datos.")

# 4. ADMIN (CONFIGURACIÓN)
if es_admin:
    with tab_admin:
        st.header("🔐 Configuración")
        
        with st.expander("🔑 USUARIOS Y HORARIOS", expanded=True):
            data_list = []
            for team, details in config_db.items():
                if isinstance(details, dict):
                    pwd = details.get("password", "")
                    ini = details.get("inicio", "00:00")
                    fin = details.get("fin", "23:59")
                else:
                    pwd = str(details)
                    ini = "00:00"
                    fin = "23:59"
                
                try:
                    t_ini = datetime.strptime(ini, "%H:%M").time()
                    t_fin = datetime.strptime(fin, "%H:%M").time()
                except:
                    t_ini, t_fin = time(0,0), time(23,59)

                data_list.append({
                    "Usuario/Equipo": team,
                    "Contraseña": pwd,
                    "Hora Inicio": t_ini,
                    "Hora Fin": t_fin
                })
            
            df_config = pd.DataFrame(data_list)
            edited_config_df = st.data_editor(
                df_config,
                column_config={
                    "Usuario/Equipo": st.column_config.TextColumn("Usuario/Equipo", required=True),
                    "Contraseña": st.column_config.TextColumn("Contraseña", required=True),
                    "Hora Inicio": st.column_config.TimeColumn("Inicio", format="HH:mm", required=True),
                    "Hora Fin": st.column_config.TimeColumn("Fin", format="HH:mm", required=True)
                },
                num_rows="dynamic",
                use_container_width=True,
                key="editor_claves_horarios"
            )
            
            if st.button("💾 GUARDAR CONFIGURACIÓN"):
                new_config_dict = {}
                for index, row in edited_config_df.iterrows():
                    team_name = str(row['Usuario/Equipo']).strip()
                    if team_name:
                        new_config_dict[team_name] = {
                            "password": str(row['Contraseña']),
                            "inicio": row['Hora Inicio'].strftime("%H:%M") if row['Hora Inicio'] else "00:00",
                            "fin": row['Hora Fin'].strftime("%H:%M") if row['Hora Fin'] else "23:59"
                        }
                guardar_configuracion(new_config_dict)
                st.success("✅ Guardado.")
                st.rerun()

        st.divider()
        with st.expander("☢️ ZONA PELIGROSA"):
            if st.button("🔴 BORRAR HISTORIAL TOTAL"):
                borrar_historial_completo()
                st.rerun()
