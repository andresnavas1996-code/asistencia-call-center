import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
import os
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Asistencia", layout="wide")

# --- ZONA HORARIA ---
try:
    import pytz
    ZONA_HORARIA = pytz.timezone('America/Bogota')
    def obtener_hora_actual(): return datetime.now(ZONA_HORARIA)
except ImportError:
    def obtener_hora_actual(): return datetime.utcnow() - timedelta(hours=5)

# Archivos
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'
ARCHIVO_PASSWORDS = 'config_passwords_v4.json' 
CARPETA_SOPORTES = 'soportes_img' 

# --- 2. FUNCIONES DE RECUPERACIÓN DE DATOS (NO DESTRUCTIVAS) ---

def cargar_empleados_seguro():
    """
    Lee la base de datos intentando recuperar la información 
    incluso si los títulos de las columnas están mal.
    """
    columnas_default = ["Equipo", "Nombre", "Cedula"]
    
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        return pd.DataFrame(columns=columnas_default)
    
    try:
        # Intento 1: Lectura estándar
        df = pd.read_csv(ARCHIVO_EMPLEADOS, dtype=str, keep_default_na=False)
        # Limpiar espacios en los nombres de columnas
        df.columns = df.columns.str.strip()
        
        # Si tiene las columnas clave, todo bien
        if 'Nombre' in df.columns and 'Equipo' in df.columns:
            return df
            
        # Intento 2: Separador punto y coma (común si se abrió en Excel)
        df = pd.read_csv(ARCHIVO_EMPLEADOS, sep=';', dtype=str, keep_default_na=False)
        df.columns = df.columns.str.strip()
        if 'Nombre' in df.columns:
            return df
            
        # Intento 3: Recuperación por posición (Si se borraron los títulos)
        # Leemos sin cabecera y asignamos nombres manualmente a las columnas 0, 1, 2
        df = pd.read_csv(ARCHIVO_EMPLEADOS, header=None, dtype=str, keep_default_na=False)
        
        nuevas_cols = {}
        if len(df.columns) >= 1: nuevas_cols[0] = 'Equipo'
        if len(df.columns) >= 2: nuevas_cols[1] = 'Nombre'
        if len(df.columns) >= 3: nuevas_cols[2] = 'Cedula'
        
        df = df.rename(columns=nuevas_cols)
        
        # Filtramos si la primera fila era basura o títulos viejos
        if not df.empty and str(df.iloc[0]['Nombre']).lower() in ['nombre', 'name']:
            df = df.iloc[1:]
            
        return df

    except Exception as e:
        st.error(f"Error recuperando datos de empleados: {e}")
        return pd.DataFrame(columns=columnas_default)

def cargar_asistencia_seguro():
    columnas_default = ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]
    if not os.path.exists(ARCHIVO_ASISTENCIA):
        return pd.DataFrame(columns=columnas_default)
    try:
        df = pd.read_csv(ARCHIVO_ASISTENCIA, dtype=str, keep_default_na=False)
        df.columns = df.columns.str.strip()
        # Rellenar columnas faltantes sin borrar filas
        for col in columnas_default:
            if col not in df.columns:
                df[col] = ""
        return df
    except:
        return pd.DataFrame(columns=columnas_default)

def reiniciar_configuracion_default():
    defaults = {
        "ADMIN": {"password": "1234", "inicio": "00:00", "fin": "23:59"},
        "Callcenter Bucaramanga": {"password": "1", "inicio": "06:00", "fin": "14:00"},
        "Callcenter Medellin": {"password": "2", "inicio": "08:00", "fin": "17:00"},
        "Callcenter Bogota": {"password": "3", "inicio": "00:00", "fin": "23:59"},
        "Servicio al cliente": {"password": "4", "inicio": "00:00", "fin": "23:59"}
    }
    try:
        with open(ARCHIVO_PASSWORDS, 'w') as f: json.dump(defaults, f)
    except: pass
    return defaults

def cargar_configuracion():
    if not os.path.exists(ARCHIVO_PASSWORDS): return reiniciar_configuracion_default()
    try:
        with open(ARCHIVO_PASSWORDS, 'r') as f:
            data = json.load(f)
            if not isinstance(data, dict): return reiniciar_configuracion_default()
            for k, v in data.items():
                if isinstance(v, str): data[k] = {"password": v, "inicio": "00:00", "fin": "23:59"}
            return data
    except: return reiniciar_configuracion_default()

def guardar_configuracion(diccionario_nuevo):
    if "ADMIN" not in diccionario_nuevo:
        diccionario_nuevo["ADMIN"] = {"password": "1234", "inicio": "00:00", "fin": "23:59"}
    with open(ARCHIVO_PASSWORDS, 'w') as f: json.dump(diccionario_nuevo, f)

def obtener_lista_equipos_dinamica():
    config = cargar_configuracion()
    return sorted([k for k in config.keys() if k != "ADMIN"])

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
        except: return True 
    return True

def asegurar_archivos():
    if not os.path.exists(CARPETA_SOPORTES): os.makedirs(CARPETA_SOPORTES)

def guardar_personal(df_nuevo, equipo_actual):
    df_todos = cargar_empleados_seguro()
    
    # Filtramos para quitar los del equipo actual y poner los nuevos
    if not df_todos.empty and 'Equipo' in df_todos.columns:
        df_todos = df_todos[df_todos['Equipo'] != equipo_actual]
    
    df_nuevo['Equipo'] = equipo_actual
    
    # Concatenamos y guardamos
    df_final = pd.concat([df_todos, df_nuevo], ignore_index=True)
    df_final.to_csv(ARCHIVO_EMPLEADOS, index=False)

def guardar_asistencia(df_registro):
    df_historico = cargar_asistencia_seguro()
    df_final = pd.concat([df_historico, df_registro], ignore_index=True)
    df_final.to_csv(ARCHIVO_ASISTENCIA, index=False)

def sobrescribir_asistencia_completa(df_completo):
    df_completo.to_csv(ARCHIVO_ASISTENCIA, index=False)

def guardar_soporte(uploaded_file, nombre_persona, fecha):
    if uploaded_file is not None:
        try:
            ext = uploaded_file.name.split('.')[-1].lower()
            nombre_archivo = f"{fecha}_{nombre_persona.replace(' ', '_')}.{ext}"
            ruta_completa = os.path.join(CARPETA_SOPORTES, nombre_archivo)
            with open(ruta_completa, "wb") as f: f.write(uploaded_file.getbuffer())
            return ruta_completa
        except: return None
    return None

def borrar_historial_completo():
    pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]).to_csv(ARCHIVO_ASISTENCIA, index=False)

# --- 3. LÓGICA PRINCIPAL ---

if 'usuario' not in st.session_state: st.session_state['usuario'] = None
config_db = cargar_configuracion()

# --- LOGIN ---
if st.session_state['usuario'] is None:
    st.title("🔐 Ingreso al Sistema")
    col1, col2 = st.columns([1, 2])
    with col1:
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            user_ok = None
            if pwd == "Admin26": user_ok = "ADMIN"
            else:
                for eq, dat in config_db.items():
                    p_stored = dat.get('password') if isinstance(dat, dict) else dat
                    if pwd == p_stored: 
                        user_ok = eq; break
            if user_ok: 
                st.session_state['usuario'] = user_ok
                st.rerun()
            else: st.error("Incorrecto.")
    st.stop() 

# --- APP ---
usuario_actual = st.session_state['usuario']
es_admin = (usuario_actual == "ADMIN")
equipos_disponibles = obtener_lista_equipos_dinamica()
en_horario = verificar_horario(usuario_actual)

with st.sidebar:
    st.write(f"Hola, **{usuario_actual}**")
    try: st.caption(f"🕒 {obtener_hora_actual().strftime('%H:%M')}")
    except: pass
    if st.button("Cerrar Sesión"):
        st.session_state['usuario'] = None
        st.rerun()

st.title(f"📋 Asistencia: {usuario_actual if not es_admin else 'Vista Global'}")
asegurar_archivos()

# ALERTA ADMIN
if es_admin:
    hoy = obtener_hora_actual().strftime("%Y-%m-%d")
    df_emp = cargar_empleados_seguro()
    df_asis = cargar_asistencia_seguro()
    
    # Verificación de seguridad antes de procesar
    if not df_emp.empty and 'Nombre' in df_emp.columns and 'Equipo' in df_emp.columns:
        df_emp['Key'] = df_emp['Equipo'].astype(str) + df_emp['Nombre'].astype(str)
        hechos = []
        if not df_asis.empty and 'Fecha' in df_asis.columns:
            df_hoy = df_asis[df_asis['Fecha'] == hoy]
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
    else:
        st.warning("⚠️ La base de datos de empleados parece estar vacía o con formato incorrecto. Ve a 'Gestionar Personal' para revisarla.")

# PESTAÑAS
if es_admin:
    tab_personal, tab_asistencia, tab_visual, tab_admin = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "📊 DASHBOARD & TRAYECTORIA", "🔐 ADMINISTRAR"])
else:
    tab_personal, tab_asistencia, tab_visual = st.tabs(["👥 MI EQUIPO", "⚡ TOMAR ASISTENCIA", "📊 MI DASHBOARD"])

# 1. GESTIÓN
with tab_personal:
    if not es_admin and not en_horario: st.error("⛔ Fuera de horario.")
    else:
        st.header("Base de Datos")
        eg = st.selectbox("Equipo:", equipos_disponibles, key="sg") if es_admin else usuario_actual
        if eg:
            df_db = cargar_empleados_seguro()
            
            # Crear estructura vacía si falla la carga
            if df_db.empty or 'Nombre' not in df_db.columns:
                df_show = pd.DataFrame(columns=['Nombre', 'Cedula'])
            else:
                df_show = df_db[df_db['Equipo'] == eg][['Nombre', 'Cedula']]
            
            df_edit = st.data_editor(df_show, num_rows="dynamic", use_container_width=True, key="edit_pers")
            
            if st.button("💾 GUARDAR CAMBIOS PERSONAL"):
                guardar_personal(df_edit, eg)
                st.success("✅ Guardado.")
                st.rerun()

# 2. ASISTENCIA
with tab_asistencia:
    if not es_admin and not en_horario: st.error("⛔ Fuera de horario.")
    else:
        st.header("Registro de Asistencia")
        if es_admin:
            c1, c2 = st.columns(2)
            ea = c1.selectbox("Equipo:", equipos_disponibles, key="sa")
            f_dt = c2.date_input("📅 Fecha:", value=obtener_hora_actual().date())
            fecha = f_dt.strftime("%Y-%m-%d")
        else:
            ea = usuario_actual
            fecha = obtener_hora_actual().strftime("%Y-%m-%d")
            st.info(f"📅 HOY: {fecha}")

        if ea:
            df_all = cargar_empleados_seguro()
            
            # Validación de columnas antes de filtrar
            if not df_all.empty and 'Equipo' in df_all.columns:
                df_base = df_all[df_all['Equipo'] == ea]
            else:
                df_base = pd.DataFrame()
                
            df_hist = cargar_asistencia_seguro()
            
            hechos = []
            if not df_hist.empty and 'Fecha' in df_hist.columns and 'Equipo' in df_hist.columns:
                hechos = df_hist[(df_hist['Fecha'] == fecha) & (df_hist['Equipo'] == ea)]['Nombre'].tolist()
            
            # Solo intentamos filtrar si df_base tiene datos y columna Nombre
            if not df_base.empty and 'Nombre' in df_base.columns:
                pendientes = df_base[~df_base['Nombre'].isin(hechos)]
            else:
                pendientes = pd.DataFrame()
            
            if not pendientes.empty:
                st.info(f"Pendientes: {len(pendientes)}")
                df_in = pendientes[['Nombre', 'Cedula']].copy()
                df_in['Estado'] = None
                df_in['Observacion'] = ""
                df_in['Soporte'] = None
                
                edited = st.data_editor(
                    df_in,
                    column_config={
                        "Nombre": st.column_config.Column(disabled=True),
                        "Cedula": st.column_config.Column(disabled=True),
                        "Estado": st.column_config.SelectboxColumn(options=["Asiste", "Ausente", "Llegada tarde", "Incapacidad", "Vacaciones"], required=True),
                        "Soporte": st.column_config.Column(disabled=True)
                    },
                    hide_index=True, use_container_width=True, key="edit_asis"
                )
                
                novs = edited[edited['Estado'].isin(["Llegada tarde", "Incapacidad"])]
                files = {}
                if not novs.empty:
                    st.warning("⚠️ Adjuntar soportes:")
                    cols = st.columns(3)
                    for i, (idx, row) in enumerate(novs.iterrows()):
                        with cols[i % 3]:
                            st.markdown(f"**{row['Nombre']}**")
                            f = st.file_uploader(f"Archivo:", type=["png","jpg","jpeg","pdf"], key=f"f_{idx}")
                            if f: files[row['Nombre']] = f
                
                if st.button("💾 GUARDAR SELECCIONADOS"):
                    to_save = edited.dropna(subset=['Estado']).copy()
                    if not to_save.empty:
                        to_save['Fecha'] = fecha
                        to_save['Equipo'] = ea
                        paths = []
                        for _, r in to_save.iterrows():
                            nm = r['Nombre']
                            paths.append(guardar_soporte(files.get(nm), nm, fecha) if nm in files else "")
                        to_save['Soporte'] = paths
                        guardar_asistencia(to_save[['Fecha', 'Equipo', 'Nombre', 'Cedula', 'Estado', 'Observacion', 'Soporte']])
                        st.success("✅ Guardado.")
                        st.rerun()
                    else: st.warning("Selecciona estados.")
            else: 
                if df_base.empty:
                    st.warning("No hay empleados cargados en este equipo.")
                else:
                    st.success("🎉 Todo listo.")

# 3. DASHBOARD
with tab_visual:
    st.header("📊 Dashboard")
    df_ver = cargar_asistencia_seguro()
    
    if not df_ver.empty and 'Fecha' in df_ver.columns:
        df_ver['Fecha_dt'] = pd.to_datetime(df_ver['Fecha']).dt.date
        c1, c2 = st.columns(2)
        fmin, fmax = df_ver['Fecha_dt'].min(), df_ver['Fecha_dt'].max()
        try: rango = c1.date_input("Rango:", [fmin, fmax])
        except: rango = [fmin, fmax]
        eq_fil = c2.multiselect("Equipo:", df_ver['Equipo'].unique()) if es_admin else None
        
        df_fil = df_ver.copy()
        if len(rango) == 2: df_fil = df_fil[(df_fil['Fecha_dt'] >= rango[0]) & (df_fil['Fecha_dt'] <= rango[1])]
        if not es_admin: df_fil = df_fil[df_fil['Equipo'] == usuario_actual]
        elif eq_fil: df_fil = df_fil[df_fil['Equipo'].isin(eq_fil)]
        
        if not df_fil.empty:
            tot = len(df_fil)
            asi = len(df_fil[df_fil['Estado'] == 'Asiste'])
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total", tot)
            k2.metric("% Asis", f"{(asi/tot)*100:.1f}%")
            
            st.divider()
            st.dataframe(df_fil, use_container_width=True)
            st.download_button("⬇️ CSV", df_fil.to_csv(index=False).encode('utf-8'), "reporte.csv", "text/csv")
            
            st.divider()
            with st.expander("🔍 Trayectoria Individual"):
                col = st.selectbox("Nombre:", df_fil['Nombre'].unique())
                if col:
                    dft = df_fil[df_fil['Nombre'] == col]
                    st.bar_chart(dft['Estado'].value_counts())
                    st.dataframe(dft[['Fecha','Estado','Observacion']])
            
            st.divider()
            with st.expander("📂 Soportes"):
                con_s = df_fil[df_fil['Soporte'].notna() & (df_fil['Soporte'].astype(str).str.len() > 5)]
                if not con_s.empty:
                    s = st.selectbox("Ver:", con_s['Nombre'] + " - " + con_s['Fecha'])
                    if s:
                        r = con_s[con_s['Nombre'] + " - " + con_s['Fecha'] == s].iloc[0]['Soporte']
                        if os.path.exists(r):
                            with open(r, "rb") as f: st.download_button("Descargar", f, os.path.basename(r))
                            if r.endswith(".pdf"): st.info("PDF")
                            else: st.image(r, width=300)
    else: st.info("Sin datos.")

# 4. ADMIN
if es_admin:
    with tab_admin:
        st.header("🔐 Admin")
        with st.expander("🔑 EQUIPOS"):
            dl = []
            for t, d in config_db.items():
                p = d.get('password','') if isinstance(d, dict) else str(d)
                i = d.get('inicio','00:00') if isinstance(d, dict) else '00:00'
                f = d.get('fin','23:59') if isinstance(d, dict) else '23:59'
                try: ti, tf = datetime.strptime(i, "%H:%M").time(), datetime.strptime(f, "%H:%M").time()
                except: ti, tf = time(0,0), time(23,59)
                dl.append({"Usuario/Equipo": t, "Contraseña": p, "Inicio": ti, "Fin": tf})
            res = st.data_editor(pd.DataFrame(dl), column_config={"Inicio":st.column_config.TimeColumn(format="HH:mm"),"Fin":st.column_config.TimeColumn(format="HH:mm")}, num_rows="dynamic")
            if st.button("💾 GUARDAR CONFIG"):
                new_c = {}
                for _, r in res.iterrows():
                    n = str(r['Usuario/Equipo']).strip()
                    if n: new_c[n] = {"password": str(r['Contraseña']), "inicio": r['Inicio'].strftime("%H:%M") if r['Inicio'] else "00:00", "fin": r['Fin'].strftime("%H:%M") if r['Fin'] else "23:59"}
                guardar_configuracion(new_c)
                st.success("Ok.")
                st.rerun()
        
        st.divider()
        st.subheader("🛠️ Corregir")
        df_full = cargar_asistencia_seguro()
        if not df_full.empty:
            df_full.insert(0, "Borrar", False)
            edf = st.data_editor(df_full, hide_index=True, use_container_width=True, key="edadm")
            if st.button("💾 APLICAR"):
                sobrescribir_asistencia_completa(edf[edf["Borrar"]==False])
                st.success("Hecho.")
                st.rerun()
            if st.button("🔴 BORRAR TODO"):
                borrar_historial_completo()
                st.rerun()
