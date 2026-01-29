import streamlit as st
import pandas as pd
from datetime import datetime, time
import os
from PIL import Image
import pytz 
import json

# --- 1. CONFIGURACIÓN ---
ZONA_HORARIA = pytz.timezone('America/Bogota')
HORA_INICIO_DEFAULT = time(0, 0)
HORA_FIN_DEFAULT = time(23, 59)

# Archivos
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'
ARCHIVO_PASSWORDS = 'config_passwords_v2.json' 
CARPETA_SOPORTES = 'soportes_img' 

# --- 2. FUNCIONES DE GESTIÓN DE DATOS ---

def obtener_hora_colombia():
    return datetime.now(ZONA_HORARIA)

def cargar_configuracion():
    """
    Carga la configuración. Si no existe, crea una por defecto.
    Retorna un diccionario: { "Equipo": {"password": "...", "inicio": "HH:MM", "fin": "HH:MM"} }
    """
    defaults = {
        "ADMIN": {"password": "1234", "inicio": "00:00", "fin": "23:59"},
        "Callcenter Bucaramanga": {"password": "1", "inicio": "06:00", "fin": "14:00"},
        "Callcenter Medellin": {"password": "2", "inicio": "08:00", "fin": "17:00"},
        "Callcenter Bogota": {"password": "3", "inicio": "00:00", "fin": "23:59"},
        "Servicio al cliente": {"password": "4", "inicio": "00:00", "fin": "23:59"}
    }
    
    if not os.path.exists(ARCHIVO_PASSWORDS):
        with open(ARCHIVO_PASSWORDS, 'w') as f:
            json.dump(defaults, f)
        return defaults
    else:
        with open(ARCHIVO_PASSWORDS, 'r') as f:
            data = json.load(f)
            # Migración rápida por si el archivo tenía formato viejo
            for k, v in data.items():
                if isinstance(v, str): 
                    data[k] = {"password": v, "inicio": "00:00", "fin": "23:59"}
            return data

def guardar_configuracion(diccionario_nuevo):
    """Guarda usuarios y horarios en JSON."""
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

# --- 3. INICIO DE LA APP ---
st.set_page_config(page_title="Gestión Asistencia", layout="wide")

if 'usuario' not in st.session_state:
    st.session_state['usuario'] = None

# Cargar configuración global
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
                    if password_input == datos['password']:
                        usuario_encontrado = equipo
                        break
            
            if usuario_encontrado:
                st.session_state['usuario'] = usuario_encontrado
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop() 

# --- APP PRINCIPAL ---
usuario_actual = st.session_state['usuario']
es_admin = (usuario_actual == "ADMIN")
equipos_disponibles = obtener_lista_equipos_dinamica()

# Verificación de Horario
en_horario = verificar_horario(usuario_actual)
config_usuario = config_db.get(usuario_actual, {})
horario_msg = f"{config_usuario.get('inicio', '00:00')} - {config_usuario.get('fin', '23:59')}"

with st.sidebar:
    st.write(f"Hola, **{usuario_actual}**")
    hora_co = obtener_hora_colombia().strftime("%H:%M")
    st.caption(f"🕒 Hora Colombia: {hora_co}")
    
    if not es_admin:
        st.caption(f"📅 Tu Horario: {horario_msg}")
        if en_horario:
            st.success("✅ En horario")
        else:
            st.error("⛔ Fuera de horario")
            
    if st.button("Cerrar Sesión"):
        st.session_state['usuario'] = None
        st.rerun()

st.title(f"📋 Asistencia: {usuario_actual if not es_admin else 'Vista Global'}")

asegurar_archivos()

# --- ALERTA ADMIN ---
if es_admin:
    fecha_hoy_alert = obtener_hora_colombia().strftime("%Y-%m-%d")
    df_empleados_all = cargar_csv(ARCHIVO_EMPLEADOS)
    df_asistencia_all = cargar_csv(ARCHIVO_ASISTENCIA)
    df_asistencia_hoy = df_asistencia_all[df_asistencia_all['Fecha'] == fecha_hoy_alert]
    
    if not df_empleados_all.empty:
        df_empleados_all['Clave'] = df_empleados_all['Equipo'] + df_empleados_all['Nombre']
        registrados_hoy = []
        if not df_asistencia_hoy.empty:
            df_asistencia_hoy['Clave'] = df_asistencia_hoy['Equipo'] + df_asistencia_hoy['Nombre']
            registrados_hoy = df_asistencia_hoy['Clave'].tolist()
        
        df_faltantes = df_empleados_all[~df_empleados_all['Clave'].isin(registrados_hoy)].copy()
        
        if not df_faltantes.empty:
            total_pendientes = len(df_faltantes)
            st.error(f"⚠️ ALERTA: Faltan {total_pendientes} personas por reportar hoy.")
            
            resumen_equipos = df_faltantes['Equipo'].value_counts().reset_index()
            resumen_equipos.columns = ['Equipo', 'Pendientes'] 
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.dataframe(resumen_equipos, hide_index=True, use_container_width=True)
            with c2:
                with st.expander("🔍 Detalle"):
                    st.dataframe(df_faltantes[['Equipo', 'Nombre']], hide_index=True, use_container_width=True)
            st.divider()

# --- PESTAÑAS ---
if es_admin:
    tab_personal, tab_asistencia, tab_visual, tab_admin = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "📊 DASHBOARD GLOBAL", "🔐 ADMINISTRAR"])
else:
    tab_personal, tab_asistencia, tab_visual = st.tabs(["👥 MI EQUIPO", "⚡ TOMAR ASISTENCIA", "📊 MI DASHBOARD"])

# ==========================================
# 1. GESTIÓN
# ==========================================
with tab_personal:
    if not es_admin and not en_horario:
        st.error(f"⛔ No puedes editar personal fuera de tu horario asignado ({horario_msg}).")
    else:
        st.header("Base de Datos de Empleados")
        if es_admin:
            equipo_gest = st.selectbox("Selecciona Equipo a Editar:", equipos_disponibles, key="sel_gest")
        else:
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
# 2. ASISTENCIA
# ==========================================
with tab_asistencia:
    if not es_admin and not en_horario:
        st.error(f"⛔ ACCESO DENEGADO: Tu horario de gestión es de {horario_msg}.")
    else:
        st.header("Registro Diario (Pendientes)")
        ahora_co = obtener_hora_colombia()
        fecha_hoy = ahora_co.strftime("%Y-%m-%d")
        
        if es_admin:
            equipo_asist = st.selectbox("Selecciona Equipo:", equipos_disponibles, key="sel_asist")
        else:
            equipo_asist = usuario_actual
        
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
                    st.success(f"✅ Registros guardados.")
                    st.rerun()
                else:
                    st.warning("Selecciona un estado.")
        else:
            if not df_personal_base.empty:
                st.success(f"🎉 Equipo al día.")
            else:
                st.warning("No hay personal registrado.")

# ==========================================
# 3. DASHBOARD
# ==========================================
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
        kpi1.metric("Total", total_regs)
        kpi2.metric("% Asistencia", f"{porc_asistencia:.1f}%")
        kpi3.metric("Llegadas Tarde", tardanzas, delta_color="inverse")
        kpi4.metric("Incap/Ausencia", incapacidades + ausencias, delta_color="inverse")
        
        st.divider()
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            if not df_show.empty:
                st.bar_chart(df_show['Estado'].value_counts(), color="#4CAF50")
        with col_graf2:
            if es_admin and not df_show.empty:
                st.bar_chart(df_show['Equipo'].value_counts(), color="#2196F3")

        st.divider()
        st.dataframe(df_show, use_container_width=True)
        
        st.subheader("🔍 Soportes")
        df_con_soporte = df_show[df_show['Soporte'].notna() & (df_show['Soporte'].str.len() > 5)]
        if not df_con_soporte.empty:
            persona_ver = st.selectbox("Ver soporte:", 
                                     df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'] + " (" + df_con_soporte['Estado'] + ")", key="viz_soporte")
            if persona_ver:
                datos_row = df_con_soporte[ (df_con_soporte['Nombre'] + " - " + df_con_soporte['Fecha'] + " (" + df_con_soporte['Estado'] + ")") == persona_ver ].iloc[0]
                ruta_img = datos_row['Soporte']
                if os.path.exists(ruta_img):
                    st.image(Image.open(ruta_img), caption=f"Soporte", width=400)
    else:
        st.info("No hay datos.")

# ==========================================
# 4. ADMINISTRAR (SOLO ADMIN)
# ==========================================
if es_admin:
    with tab_admin:
        st.header("🔐 Administración Global")
        
        # --- GESTIÓN DE USUARIOS Y HORARIOS ---
        with st.expander("🔑 GESTIÓN DE USUARIOS Y HORARIOS", expanded=True):
            st.info("Configura usuarios, contraseñas y franja horaria de operación (24h).")
            
            # 1. Convertir Diccionario JSON a DataFrame Plano para la Tabla
            data_list = []
            for team, details in config_db.items():
                if isinstance(details, dict):
                    pwd = details.get("password", "")
                    ini = details.get("inicio", "00:00")
                    fin = details.get("fin", "23:59")
                else: # Soporte legacy
                    pwd = str(details)
                    ini = "00:00"
                    fin = "23:59"
                
                # Convertir a objetos Time para que el editor muestre reloj
                try:
                    t_ini = datetime.strptime(ini, "%H:%M").time()
                    t_fin = datetime.strptime(fin, "%H:%M").time()
                except:
                    t_ini = time(0,0)
                    t_fin = time(23,59)

                data_list.append({
                    "Usuario/Equipo": team,
                    "Contraseña": pwd,
                    "Hora Inicio": t_ini,
                    "Hora Fin": t_fin
                })
            
            df_config = pd.DataFrame(data_list)

            # 2. Editor con Columnas de Tiempo
            edited_config_df = st.data_editor(
                df_config,
                column_config={
                    "Usuario/Equipo": st.column_config.TextColumn("Usuario/Equipo", required=True),
                    "Contraseña": st.column_config.TextColumn("Contraseña", required=True),
                    "Hora Inicio": st.column_config.TimeColumn("Hora Inicio", format="HH:mm", required=True),
                    "Hora Fin": st.column_config.TimeColumn("Hora Fin", format="HH:mm", required=True)
                },
                num_rows="dynamic",
                use_container_width=True,
                key="editor_claves_horarios"
            )
            
            if st.button("💾 GUARDAR CONFIGURACIÓN"):
                # 3. Reconstruir Diccionario JSON desde el DataFrame Editado
                new_config_dict = {}
                for index, row in edited_config_df.iterrows():
                    team_name = row['Usuario/Equipo']
                    # Convertir objetos Time de vuelta a String HH:MM
                    t_start_str = row['Hora Inicio'].strftime("%H:%M") if row['Hora Inicio'] else "00:00"
                    t_end_str = row['Hora Fin'].strftime("%H:%M") if row['Hora Fin'] else "23:59"
                    
                    new_config_dict[team_name] = {
                        "password": str(row['Contraseña']),
                        "inicio": t_start_str,
                        "fin": t_end_str
                    }
                
                guardar_configuracion(new_config_dict)
                st.success("✅ Usuarios y Horarios actualizados correctamente. Recargando...")
                st.rerun()

        st.divider()

        st.subheader("🛠️ Corregir Historial")
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

            with st.expander("☢️ BORRAR TODO EL HISTORIAL"):
                if st.button("🔴 CONFIRMAR BORRADO TOTAL", type="primary"):
                    borrar_historial_completo()
                    st.rerun()
