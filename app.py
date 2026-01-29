import streamlit as st
import pandas as pd
from datetime import datetime, time
import os
import pytz 
import json

# --- 1. CONFIGURACIÓN ---
# Configuración de la página (DEBE IR DE PRIMERO)
st.set_page_config(page_title="Gestión Asistencia", layout="wide")

try:
    ZONA_HORARIA = pytz.timezone('America/Bogota')
except:
    ZONA_HORARIA = pytz.utc

# Archivos
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'
ARCHIVO_PASSWORDS = 'config_passwords_v3.json' 
CARPETA_SOPORTES = 'soportes_img' 

# --- 2. FUNCIONES ROBUSTAS ---

def obtener_hora_colombia():
    return datetime.now(ZONA_HORARIA)

def reiniciar_configuracion_default():
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
    if not os.path.exists(ARCHIVO_PASSWORDS):
        return reiniciar_configuracion_default()
    try:
        with open(ARCHIVO_PASSWORDS, 'r') as f:
            data = json.load(f)
            if not data or not isinstance(data, dict): return reiniciar_configuracion_default()
            for k, v in data.items():
                if isinstance(v, str): data[k] = {"password": v, "inicio": "00:00", "fin": "23:59"}
            return data
    except:
        return reiniciar_configuracion_default()

def guardar_configuracion(diccionario_nuevo):
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
        try:
            h_inicio = datetime.strptime(datos.get("inicio", "00:00"), "%H:%M").time()
            h_fin = datetime.strptime(datos.get("fin", "23:59"), "%H:%M").time()
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
        try:
            df_temp = pd.read_csv(ARCHIVO_ASISTENCIA)
            if "Soporte" not in df_temp.columns:
                df_temp["Soporte"] = None
                df_temp.to_csv(ARCHIVO_ASISTENCIA, index=False)
        except:
            pass

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
    """Sobrescribe el archivo de asistencia con los datos editados."""
    cols_reales = ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]
    # Aseguramos que existan las columnas, si falta alguna la llenamos
    for col in cols_reales:
        if col not in df_completo.columns:
            df_completo[col] = ""
            
    df_final = df_completo[cols_reales]
    df_final.to_csv(ARCHIVO_ASISTENCIA, index=False)

def guardar_soporte(uploaded_file, nombre_persona, fecha):
    """Guarda imagen o PDF."""
    if uploaded_file is not None:
        try:
            # Obtener extensión original (jpg, png, pdf)
            ext = uploaded_file.name.split('.')[-1].lower()
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

# --- 3. LÓGICA PRINCIPAL ---

if 'usuario' not in st.session_state:
    st.session_state['usuario'] = None

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
            if password_input == "Admin26":
                usuario_encontrado = "ADMIN"
            else:
                for equipo, datos in config_db.items():
                    if isinstance(datos, dict) and password_input == datos.get('password'):
                        usuario_encontrado = equipo
                        break
                    elif isinstance(datos, str) and password_input == datos:
                        usuario_encontrado = equipo
                        break
            
            if usuario_encontrado:
                st.session_state['usuario'] = usuario_encontrado
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop() 

# --- APP ---
usuario_actual = st.session_state['usuario']
es_admin = (usuario_actual == "ADMIN")
equipos_disponibles = obtener_lista_equipos_dinamica()
en_horario = verificar_horario(usuario_actual)

with st.sidebar:
    st.write(f"Hola, **{usuario_actual}**")
    try:
        hora_co = obtener_hora_colombia().strftime("%H:%M")
        st.caption(f"🕒 Hora CO: {hora_co}")
    except:
        pass
    if st.button("Cerrar Sesión"):
        st.session_state['usuario'] = None
        st.rerun()

st.title(f"📋 Asistencia: {usuario_actual if not es_admin else 'Vista Global'}")
asegurar_archivos()

# ALERTA ADMIN
if es_admin:
    fecha_hoy = obtener_hora_colombia().strftime("%Y-%m-%d")
    df_emp = cargar_csv(ARCHIVO_EMPLEADOS)
    df_asis = cargar_csv(ARCHIVO_ASISTENCIA)
    
    if not df_emp.empty:
        # Claves compuestas
        df_emp['Key'] = df_emp['Equipo'].astype(str) + df_emp['Nombre'].astype(str)
        hechos = []
        if not df_asis.empty:
            df_hoy = df_asis[df_asis['Fecha'] == fecha_hoy]
            if not df_hoy.empty:
                df_hoy['Key'] = df_hoy['Equipo'].astype(str) + df_hoy['Nombre'].astype(str)
                hechos = df_hoy['Key'].tolist()
        
        pendientes = df_emp[~df_emp['Key'].isin(hechos)]
        
        if not pendientes.empty:
            st.error(f"⚠️ Faltan {len(pendientes)} personas hoy.")
            resumen = pendientes['Equipo'].value_counts().reset_index()
            resumen.columns = ['Equipo', 'Pendientes']
            c1, c2 = st.columns([1, 2])
            with c1: st.dataframe(resumen, hide_index=True, use_container_width=True)
            with c2: 
                with st.expander("Ver lista"): st.dataframe(pendientes[['Equipo', 'Nombre']], hide_index=True)
            st.divider()

# PESTAÑAS
if es_admin:
    tab_personal, tab_asistencia, tab_visual, tab_admin = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "📊 DASHBOARD", "🔐 ADMINISTRAR"])
else:
    tab_personal, tab_asistencia, tab_visual = st.tabs(["👥 MI EQUIPO", "⚡ TOMAR ASISTENCIA", "📊 MI DASHBOARD"])

# 1. GESTIÓN
with tab_personal:
    if not es_admin and not en_horario:
        st.error("⛔ Fuera de horario.")
    else:
        st.header("Base de Datos")
        equipo_gest = st.selectbox("Equipo:", equipos_disponibles, key="sg") if es_admin else usuario_actual
        
        if equipo_gest:
            df_db = cargar_csv(ARCHIVO_EMPLEADOS)
            df_show = df_db[df_db['Equipo'] == equipo_gest][['Nombre', 'Cedula']] if not df_db.empty and 'Equipo' in df_db.columns else pd.DataFrame(columns=['Nombre', 'Cedula'])
            
            df_edit = st.data_editor(df_show, num_rows="dynamic", use_container_width=True, key="edit_pers")
            
            if st.button("💾 GUARDAR CAMBIOS PERSONAL"):
                guardar_personal(df_edit, equipo_gest)
                st.success("✅ Guardado.")
                st.rerun()

# 2. ASISTENCIA
with tab_asistencia:
    if not es_admin and not en_horario:
        st.error("⛔ Fuera de horario.")
    else:
        st.header("Registro Diario")
        fecha = obtener_hora_colombia().strftime("%Y-%m-%d")
        equipo_asist = st.selectbox("Equipo:", equipos_disponibles, key="sa") if es_admin else usuario_actual
        
        if equipo_asist:
            df_all_emp = cargar_csv(ARCHIVO_EMPLEADOS)
            df_base = df_all_emp[df_all_emp['Equipo'] == equipo_asist] if not df_all_emp.empty and 'Equipo' in df_all_emp.columns else pd.DataFrame()
            
            df_hist = cargar_csv(ARCHIVO_ASISTENCIA)
            hechos = df_hist[(df_hist['Fecha'] == fecha) & (df_hist['Equipo'] == equipo_asist)]['Nombre'].tolist() if not df_hist.empty and 'Fecha' in df_hist.columns else []
            
            pendientes = df_base[~df_base['Nombre'].isin(hechos)]
            
            if not pendientes.empty:
                st.info(f"Pendientes: {len(pendientes)}")
                df_input = pendientes[['Nombre', 'Cedula']].copy()
                df_input['Estado'] = None
                df_input['Observacion'] = ""
                df_input['Soporte'] = None
                
                edited = st.data_editor(
                    df_input,
                    column_config={
                        "Nombre": st.column_config.Column(disabled=True),
                        "Cedula": st.column_config.Column(disabled=True),
                        "Estado": st.column_config.SelectboxColumn("Estado", options=["Asiste", "Ausente", "Llegada tarde", "Incapacidad", "Vacaciones"], required=True),
                        "Soporte": st.column_config.Column(disabled=True)
                    },
                    hide_index=True, use_container_width=True, key="edit_assist"
                )
                
                # Carga de adjuntos
                novedades = edited[edited['Estado'].isin(["Llegada tarde", "Incapacidad"])]
                files = {}
                if not novedades.empty:
                    st.warning("⚠️ Cargar soportes (PDF o Imagen):")
                    cols = st.columns(3)
                    for i, (idx, row) in enumerate(novedades.iterrows()):
                        with cols[i % 3]:
                            st.markdown(f"**{row['Nombre']}**")
                            # ACEPTAMOS PDF AHORA
                            f = st.file_uploader(f"Archivo:", type=["png", "jpg", "jpeg", "pdf"], key=f"f_{idx}")
                            if f: files[row['Nombre']] = f
                
                if st.button("💾 GUARDAR SELECCIONADOS"):
                    to_save = edited.dropna(subset=['Estado']).copy()
                    if not to_save.empty:
                        to_save['Fecha'] = fecha
                        to_save['Equipo'] = equipo_asist
                        paths = []
                        for _, r in to_save.iterrows():
                            nm = r['Nombre']
                            paths.append(guardar_soporte(files.get(nm), nm, fecha) if nm in files else "")
                        to_save['Soporte'] = paths
                        guardar_asistencia(to_save[['Fecha', 'Equipo', 'Nombre', 'Cedula', 'Estado', 'Observacion', 'Soporte']])
                        st.success("✅ Guardado.")
                        st.rerun()
                    else:
                        st.warning("Selecciona estados.")
            else:
                st.success("🎉 Al día.")

# 3. DASHBOARD (VISOR DE SOPORTES MEJORADO)
with tab_visual:
    st.header("📊 Dashboard")
    df_ver = cargar_csv(ARCHIVO_ASISTENCIA)
    if not df_ver.empty:
        if not es_admin: df_ver = df_ver[df_ver['Equipo'] == usuario_actual]
        
        c1, c2 = st.columns(2)
        with c1: 
            fechas = st.multiselect("Fecha:", df_ver['Fecha'].unique())
        with c2:
            equipos_filtro = st.multiselect("Equipo:", df_ver['Equipo'].unique()) if es_admin else None
            
        df_fil = df_ver.copy()
        if fechas: df_fil = df_fil[df_fil['Fecha'].isin(fechas)]
        if equipos_filtro: df_fil = df_fil[df_fil['Equipo'].isin(equipos_filtro)]
        
        st.dataframe(df_fil, use_container_width=True)
        
        # --- VISOR Y DESCARGA ---
        st.divider()
        st.subheader("📂 Visor y Descarga de Soportes")
        # Filtramos los que tienen soporte válido (ruta larga)
        con_soporte = df_fil[df_fil['Soporte'].notna() & (df_fil['Soporte'].astype(str).str.len() > 5)]
        
        if not con_soporte.empty:
            sel = st.selectbox("Seleccionar registro:", con_soporte['Nombre'] + " - " + con_soporte['Fecha'], key="visor_sel")
            if sel:
                row = con_soporte[con_soporte['Nombre'] + " - " + con_soporte['Fecha'] == sel].iloc[0]
                ruta = row['Soporte']
                
                if os.path.exists(ruta):
                    # BOTÓN DE DESCARGA
                    with open(ruta, "rb") as file:
                        st.download_button(
                            label="⬇️ DESCARGAR ARCHIVO",
                            data=file,
                            file_name=os.path.basename(ruta),
                            mime="application/pdf" if ruta.endswith(".pdf") else "image/jpeg"
                        )
                    
                    # VISTA PREVIA
                    if ruta.endswith(".pdf"):
                        st.info("📄 El archivo es un PDF. Usa el botón de arriba para descargarlo y verlo.")
                    else:
                        st.image(ruta, caption="Vista previa", width=400)
                else:
                    st.error("❌ El archivo no se encuentra en el servidor (pudo haber sido borrado).")
        else:
            st.info("No hay soportes en los registros filtrados.")
    else:
        st.info("Sin datos.")

# 4. ADMIN (CORRECCIONES)
if es_admin:
    with tab_admin:
        st.header("🔐 Admin")
        with st.expander("🔑 USUARIOS / HORARIOS"):
            data_list = []
            for t, d in config_db.items():
                p = d.get('password','') if isinstance(d, dict) else str(d)
                i = d.get('inicio','00:00') if isinstance(d, dict) else '00:00'
                f = d.get('fin','23:59') if isinstance(d, dict) else '23:59'
                try: 
                    ti = datetime.strptime(i, "%H:%M").time()
                    tf = datetime.strptime(f, "%H:%M").time()
                except: ti, tf = time(0,0), time(23,59)
                data_list.append({"Usuario/Equipo": t, "Contraseña": p, "Inicio": ti, "Fin": tf})
            
            df_conf = pd.DataFrame(data_list)
            res = st.data_editor(
                df_conf, 
                column_config={"Inicio": st.column_config.TimeColumn(format="HH:mm"), "Fin": st.column_config.TimeColumn(format="HH:mm")},
                num_rows="dynamic", key="edit_conf"
            )
            if st.button("💾 GUARDAR CONFIG"):
                new_c = {}
                for _, r in res.iterrows():
                    nm = str(r['Usuario/Equipo']).strip()
                    if nm:
                        new_c[nm] = {
                            "password": str(r['Contraseña']),
                            "inicio": r['Inicio'].strftime("%H:%M") if r['Inicio'] else "00:00",
                            "fin": r['Fin'].strftime("%H:%M") if r['Fin'] else "23:59"
                        }
                guardar_configuracion(new_c)
                st.success("Guardado.")
                st.rerun()
        
        st.divider()
        st.subheader("🛠️ Corregir Historial (Edición Total)")
        df_full = cargar_csv(ARCHIVO_ASISTENCIA)
        if not df_full.empty:
            df_full.insert(0, "Borrar", False)
            # Editor FULL sin filtros ocultos para evitar errores de guardado
            edited_full = st.data_editor(
                df_full,
                column_config={
                    "Borrar": st.column_config.CheckboxColumn(default=False),
                    "Fecha": st.column_config.Column(disabled=True), # Fecha fija por seguridad
                    "Equipo": st.column_config.Column(disabled=True),
                    "Nombre": st.column_config.Column(disabled=True),
                    "Estado": st.column_config.SelectboxColumn(options=["Asiste", "Ausente", "Llegada tarde", "Incapacidad", "Vacaciones"]),
                    "Soporte": st.column_config.Column(disabled=True)
                },
                hide_index=True, use_container_width=True, key="edit_full_admin"
            )
            
            if st.button("💾 APLICAR CORRECCIONES"):
                # Filtramos los que NO están marcados para borrar
                final_df = edited_full[edited_full["Borrar"] == False]
                sobrescribir_asistencia_completa(final_df)
                st.success("✅ Historial actualizado correctamente.")
                st.rerun()
                
            with st.expander("☢️ BORRAR TODO"):
                if st.button("🔴 CONFIRMAR BORRADO"):
                    borrar_historial_completo()
                    st.rerun()
