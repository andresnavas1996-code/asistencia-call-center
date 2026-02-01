import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
import os
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Asistencia", layout="wide")

# --- MANEJO DE ZONA HORARIA A PRUEBA DE FALLOS ---
try:
    import pytz
    ZONA_HORARIA = pytz.timezone('America/Bogota')
    def obtener_hora_actual():
        return datetime.now(ZONA_HORARIA)
except ImportError:
    def obtener_hora_actual():
        return datetime.utcnow() - timedelta(hours=5)

# Archivos
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'
ARCHIVO_PASSWORDS = 'config_passwords_v4.json' 
CARPETA_SOPORTES = 'soportes_img' 

# --- 2. FUNCIONES ROBUSTAS (CON AUTORREPARACIÓN) ---

def reiniciar_configuracion_default():
    defaults = {
        "ADMIN": {"password": "1234", "inicio": "00:00", "fin": "23:59"},
        "Callcenter Bucaramanga": {"password": "1", "inicio": "06:00", "fin": "14:00"},
        "Callcenter Medellin": {"password": "2", "inicio": "08:00", "fin": "17:00"},
        "Callcenter Bogota": {"password": "3", "inicio": "00:00", "fin": "23:59"},
        "Servicio al cliente": {"password": "4", "inicio": "00:00", "fin": "23:59"}
    }
    try:
        with open(ARCHIVO_PASSWORDS, 'w') as f:
            json.dump(defaults, f)
    except:
        pass
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
            hora_actual = obtener_hora_actual().time()
            return h_inicio <= hora_actual <= h_fin
        except:
            return True 
    return True

def asegurar_archivos():
    if not os.path.exists(CARPETA_SOPORTES):
        os.makedirs(CARPETA_SOPORTES)
        
    # --- AUTORREPARACIÓN DE EMPLEADOS ---
    columnas_emp = ["Equipo", "Nombre", "Cedula"]
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        pd.DataFrame(columns=columnas_emp).to_csv(ARCHIVO_EMPLEADOS, index=False)
    else:
        try:
            df = pd.read_csv(ARCHIVO_EMPLEADOS)
            # Si faltan columnas clave, regeneramos el archivo
            if 'Nombre' not in df.columns or 'Equipo' not in df.columns:
                pd.DataFrame(columns=columnas_emp).to_csv(ARCHIVO_EMPLEADOS, index=False)
        except:
            pd.DataFrame(columns=columnas_emp).to_csv(ARCHIVO_EMPLEADOS, index=False)

    # --- AUTORREPARACIÓN DE ASISTENCIA ---
    columnas_asis = ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]
    if not os.path.exists(ARCHIVO_ASISTENCIA):
        pd.DataFrame(columns=columnas_asis).to_csv(ARCHIVO_ASISTENCIA, index=False)
    else:
        try:
            df = pd.read_csv(ARCHIVO_ASISTENCIA)
            if 'Nombre' not in df.columns or 'Fecha' not in df.columns:
                pd.DataFrame(columns=columnas_asis).to_csv(ARCHIVO_ASISTENCIA, index=False)
        except:
            pd.DataFrame(columns=columnas_asis).to_csv(ARCHIVO_ASISTENCIA, index=False)

def cargar_csv(archivo):
    asegurar_archivos() # Ejecuta la reparación antes de leer
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
    for col in cols_reales:
        if col not in df_completo.columns:
            df_completo[col] = ""
    df_final = df_completo[cols_reales]
    df_final.to_csv(ARCHIVO_ASISTENCIA, index=False)

def guardar_soporte(uploaded_file, nombre_persona, fecha):
    if uploaded_file is not None:
        try:
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
        hora_co = obtener_hora_actual().strftime("%H:%M")
        st.caption(f"🕒 Hora CO: {hora_co}")
    except: pass
    
    if st.button("Cerrar Sesión"):
        st.session_state['usuario'] = None
        st.rerun()

st.title(f"📋 Asistencia: {usuario_actual if not es_admin else 'Vista Global'}")
asegurar_archivos()

# ALERTA ADMIN
if es_admin:
    fecha_hoy = obtener_hora_actual().strftime("%Y-%m-%d")
    df_emp = cargar_csv(ARCHIVO_EMPLEADOS)
    df_asis = cargar_csv(ARCHIVO_ASISTENCIA)
    
    if not df_emp.empty:
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
    tab_personal, tab_asistencia, tab_visual, tab_admin = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "📊 DASHBOARD & TRAYECTORIA", "🔐 ADMINISTRAR"])
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
        st.header("Registro de Asistencia")
        if es_admin:
            c_eq, c_fe = st.columns(2)
            with c_eq: equipo_asist = st.selectbox("Equipo:", equipos_disponibles, key="sa")
            with c_fe: 
                fecha_dt = st.date_input("📅 Fecha de Registro:", value=obtener_hora_actual().date())
                fecha = fecha_dt.strftime("%Y-%m-%d")
        else:
            equipo_asist = usuario_actual
            fecha = obtener_hora_actual().strftime("%Y-%m-%d")
            st.info(f"📅 HOY: {fecha}")

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
                novedades = edited[edited['Estado'].isin(["Llegada tarde", "Incapacidad"])]
                files = {}
                if not novedades.empty:
                    st.warning("⚠️ Cargar soportes (PDF o Imagen):")
                    cols = st.columns(3)
                    for i, (idx, row) in enumerate(novedades.iterrows()):
                        with cols[i % 3]:
                            st.markdown(f"**{row['Nombre']}**")
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
                        st.success(f"✅ Guardado para el {fecha}.")
                        st.rerun()
                    else:
                        st.warning("Selecciona estados.")
            else:
                st.success(f"🎉 Gestionado para el {fecha}.")

# 3. DASHBOARD
with tab_visual:
    st.header("📊 Dashboard")
    df_ver = cargar_csv(ARCHIVO_ASISTENCIA)
    if not df_ver.empty:
        df_ver['Fecha_dt'] = pd.to_datetime(df_ver['Fecha']).dt.date
        c1, c2 = st.columns(2)
        with c1:
            fmin = df_ver['Fecha_dt'].min()
            fmax = df_ver['Fecha_dt'].max()
            try: rango = st.date_input("📅 Rango:", [fmin, fmax])
            except: rango = [fmin, fmax]
        with c2:
            eq_fil = st.multiselect("Equipo:", df_ver['Equipo'].unique()) if es_admin else None
            
        df_fil = df_ver.copy()
        if len(rango) == 2: df_fil = df_fil[(df_fil['Fecha_dt'] >= rango[0]) & (df_fil['Fecha_dt'] <= rango[1])]
        if not es_admin: df_fil = df_fil[df_fil['Equipo'] == usuario_actual]
        elif eq_fil: df_fil = df_fil[df_fil['Equipo'].isin(eq_fil)]
        
        if not df_fil.empty:
            tot = len(df_fil)
            asi = len(df_fil[df_fil['Estado'] == 'Asiste'])
            tar = len(df_fil[df_fil['Estado'] == 'Llegada tarde'])
            aus = len(df_fil[df_fil['Estado'].isin(['Ausente', 'Incapacidad'])])
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total", tot)
            k2.metric("% Asis", f"{(asi/tot)*100:.1f}%")
            k3.metric("Tardes", tar, delta_color="inverse")
            k4.metric("Faltas", aus, delta_color="inverse")
            st.divider()
            st.dataframe(df_fil, use_container_width=True)
            csv = df_fil.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Descargar CSV", csv, "reporte.csv", "text/csv")
            
            st.divider()
            st.subheader("👤 Trayectoria")
            with st.expander("🔍 Consultar Individual"):
                col = st.selectbox("Colaborador:", df_fil['Nombre'].unique())
                if col:
                    df_t = df_fil[df_fil['Nombre'] == col]
                    st.bar_chart(df_t['Estado'].value_counts())
                    st.dataframe(df_t[['Fecha', 'Estado', 'Observacion']], use_container_width=True)

            st.divider()
            st.subheader("📂 Soportes")
            con_sop = df_fil[df_fil['Soporte'].notna() & (df_fil['Soporte'].astype(str).str.len() > 5)]
            if not con_sop.empty:
                sel = st.selectbox("Ver:", con_sop['Nombre'] + " - " + con_sop['Fecha'], key="vs")
                if sel:
                    r = con_sop[con_sop['Nombre'] + " - " + con_sop['Fecha'] == sel].iloc[0]['Soporte']
                    if os.path.exists(r):
                        with open(r, "rb") as f: st.download_button("⬇️ Descargar", f, os.path.basename(r))
                        if r.endswith(".pdf"): st.info("PDF disponible.")
                        else: st.image(r, width=400)
    else: st.info("Sin datos.")

# 4. ADMIN
if es_admin:
    with tab_admin:
        st.header("🔐 Admin")
        with st.expander("🔑 EQUIPOS Y HORARIOS"):
            d_l = []
            for t, d in config_db.items():
                p = d.get('password','') if isinstance(d, dict) else str(d)
                i = d.get('inicio','00:00') if isinstance(d, dict) else '00:00'
                f = d.get('fin','23:59') if isinstance(d, dict) else '23:59'
                try: ti, tf = datetime.strptime(i, "%H:%M").time(), datetime.strptime(f, "%H:%M").time()
                except: ti, tf = time(0,0), time(23,59)
                d_l.append({"Usuario/Equipo": t, "Contraseña": p, "Inicio": ti, "Fin": tf})
            res = st.data_editor(pd.DataFrame(d_l), column_config={"Inicio": st.column_config.TimeColumn(format="HH:mm"), "Fin": st.column_config.TimeColumn(format="HH:mm")}, num_rows="dynamic", key="ec")
            if st.button("💾 GUARDAR"):
                new_c = {}
                for _, r in res.iterrows():
                    nm = str(r['Usuario/Equipo']).strip()
                    if nm: new_c[nm] = {"password": str(r['Contraseña']), "inicio": r['Inicio'].strftime("%H:%M") if r['Inicio'] else "00:00", "fin": r['Fin'].strftime("%H:%M") if r['Fin'] else "23:59"}
                guardar_configuracion(new_c)
                st.success("Guardado.")
                st.rerun()
        
        st.divider()
        st.subheader("🛠️ Corregir")
        df_full = cargar_csv(ARCHIVO_ASISTENCIA)
        if not df_full.empty:
            df_full.insert(0, "Borrar", False)
            ed_f = st.data_editor(df_full, hide_index=True, use_container_width=True, key="efa")
            if st.button("💾 APLICAR"):
                sobrescribir_asistencia_completa(ed_f[ed_f["Borrar"] == False])
                st.success("Hecho.")
                st.rerun()
            if st.button("🔴 BORRAR TODO"):
                borrar_historial_completo()
                st.rerun()
