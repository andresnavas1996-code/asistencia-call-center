import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
import os
import json
import shutil

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Asistencia", layout="wide", page_icon="🛡️")

# --- ZONA HORARIA ROBUSTA ---
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

# --- 2. SISTEMA DE SEGURIDAD (AUTOCURACIÓN Y BACKUPS) ---

def garantizar_columnas(df, columnas_requeridas):
    """Asegura que las columnas existan en memoria para evitar crash."""
    if df is None or df.empty:
        return pd.DataFrame(columns=columnas_requeridas)
    
    for col in columnas_requeridas:
        if col not in df.columns:
            df[col] = "" 
    return df

def crear_backup(archivo):
    """Crea una copia de seguridad (.bak) antes de modificar el archivo original."""
    if os.path.exists(archivo) and os.path.getsize(archivo) > 0:
        try: shutil.copy(archivo, f"{archivo}.bak")
        except: pass

def recuperar_desde_backup(archivo):
    """Fuerza la restauración desde el archivo .bak"""
    backup = f"{archivo}.bak"
    if os.path.exists(backup) and os.path.getsize(backup) > 0:
        try:
            shutil.copy(backup, archivo)
            return True
        except: return False
    return False

def cargar_csv_inteligente(archivo, columnas_esperadas):
    """
    Lectura blindada. Si falla el principal, intenta usar el backup automáticamente.
    Si ambos fallan, devuelve un DataFrame vacío pero con la estructura correcta.
    """
    # 1. Si no existe o está vacío, intentamos auto-recuperar del backup
    if not os.path.exists(archivo) or os.path.getsize(archivo) == 0:
        recuperar_desde_backup(archivo)

    try:
        # 2. Intento de lectura estándar
        if not os.path.exists(archivo): return pd.DataFrame(columns=columnas_esperadas)
        
        df = pd.read_csv(archivo, dtype=str, keep_default_na=False)
        df.columns = df.columns.str.strip()
        
        # 3. Validación de estructura
        if not set(columnas_esperadas).issubset(df.columns):
            # Intento de lectura sin headers (recuperación de datos crudos)
            df_raw = pd.read_csv(archivo, header=None, dtype=str, keep_default_na=False)
            if len(df_raw.columns) >= len(columnas_esperadas):
                mapa = {i: col for i, col in enumerate(columnas_esperadas)}
                df_raw = df_raw.rename(columns=mapa)
                # Filtramos header viejo si existe
                if not df_raw.empty and str(df_raw.iloc[0][columnas_esperadas[0]]).lower() == columnas_esperadas[0].lower():
                    df_raw = df_raw.iloc[1:]
                return garantizar_columnas(df_raw, columnas_esperadas)
        
        return garantizar_columnas(df, columnas_esperadas)

    except Exception:
        return pd.DataFrame(columns=columnas_esperadas)

def guardar_csv_seguro(df, archivo):
    """Crea backup y luego guarda."""
    crear_backup(archivo)
    df.to_csv(archivo, index=False)

def asegurar_archivos():
    """Verifica integridad al inicio."""
    if not os.path.exists(CARPETA_SOPORTES): os.makedirs(CARPETA_SOPORTES)
    # Si faltan archivos, intentar recuperar de backup o crear nuevos
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        if not recuperar_desde_backup(ARCHIVO_EMPLEADOS):
            pd.DataFrame(columns=["Equipo", "Nombre", "Cedula"]).to_csv(ARCHIVO_EMPLEADOS, index=False)
            
    if not os.path.exists(ARCHIVO_ASISTENCIA):
        if not recuperar_desde_backup(ARCHIVO_ASISTENCIA):
            pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]).to_csv(ARCHIVO_ASISTENCIA, index=False)

# --- 3. LÓGICA DE NEGOCIO ---

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
    if "ADMIN" not in diccionario_nuevo: diccionario_nuevo["ADMIN"] = {"password": "1234", "inicio": "00:00", "fin": "23:59"}
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

def guardar_personal(df_nuevo, equipo_actual):
    cols = ["Equipo", "Nombre", "Cedula"]
    df_todos = cargar_csv_inteligente(ARCHIVO_EMPLEADOS, cols)
    if not df_todos.empty: df_todos = df_todos[df_todos['Equipo'] != equipo_actual]
    
    df_nuevo = garantizar_columnas(df_nuevo, cols)
    df_nuevo['Equipo'] = equipo_actual
    
    df_final = pd.concat([df_todos, df_nuevo], ignore_index=True)
    guardar_csv_seguro(df_final, ARCHIVO_EMPLEADOS)

def guardar_asistencia(df_registro):
    cols = ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]
    df_historico = cargar_csv_inteligente(ARCHIVO_ASISTENCIA, cols)
    df_final = pd.concat([df_historico, df_registro], ignore_index=True)
    guardar_csv_seguro(df_final, ARCHIVO_ASISTENCIA)

def sobrescribir_asistencia_completa(df_completo):
    cols = ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]
    df_completo = garantizar_columnas(df_completo, cols)
    guardar_csv_seguro(df_completo[cols], ARCHIVO_ASISTENCIA)

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
    crear_backup(ARCHIVO_ASISTENCIA)
    pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"]).to_csv(ARCHIVO_ASISTENCIA, index=False)

def reparar_base_datos_empleados():
    crear_backup(ARCHIVO_EMPLEADOS)
    cols = ["Equipo", "Nombre", "Cedula"]
    try:
        df = pd.read_csv(ARCHIVO_EMPLEADOS, header=None, dtype=str)
        if len(df.columns) >= 3:
            df = df.rename(columns={0: 'Equipo', 1: 'Nombre', 2: 'Cedula'})
            df.to_csv(ARCHIVO_EMPLEADOS, index=False)
            return True
    except:
        pd.DataFrame(columns=cols).to_csv(ARCHIVO_EMPLEADOS, index=False)
        return True
    return False

# --- 4. INTERFAZ ---

if 'usuario' not in st.session_state: st.session_state['usuario'] = None
config_db = cargar_configuracion()
asegurar_archivos() 

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
                    if pwd == p_stored: user_ok = eq; break
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

st.title(f"📊 Asistencia: {usuario_actual if not es_admin else 'Vista Gerencial'}")

# ALERTA ADMIN
if es_admin:
    hoy = obtener_hora_actual().strftime("%Y-%m-%d")
    df_emp = cargar_csv_inteligente(ARCHIVO_EMPLEADOS, ["Equipo", "Nombre", "Cedula"])
    df_asis = cargar_csv_inteligente(ARCHIVO_ASISTENCIA, ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"])
    
    if not df_emp.empty:
        df_emp = garantizar_columnas(df_emp, ["Equipo", "Nombre"])
        df_emp['Key'] = df_emp['Equipo'].astype(str) + df_emp['Nombre'].astype(str)
        
        hechos = []
        if not df_asis.empty:
            df_asis = garantizar_columnas(df_asis, ["Fecha", "Equipo", "Nombre"])
            df_hoy = df_asis[df_asis['Fecha'] == hoy]
            if not df_hoy.empty:
                df_hoy['Key'] = df_hoy['Equipo'].astype(str) + df_hoy['Nombre'].astype(str)
                hechos = df_hoy['Key'].tolist()
        
        pendientes = df_emp[~df_emp['Key'].isin(hechos)]
        if not pendientes.empty:
            st.error(f"⚠️ Alerta: Faltan {len(pendientes)} reportes hoy.")
            if 'Equipo' in pendientes.columns:
                resumen = pendientes['Equipo'].value_counts().reset_index()
                resumen.columns = ['Equipo', 'Pendientes']
                c1, c2 = st.columns([1, 2])
                with c1: st.dataframe(resumen, hide_index=True, use_container_width=True)
                with c2: 
                    with st.expander("Ver lista"): st.dataframe(pendientes[['Equipo', 'Nombre']], hide_index=True)
            st.divider()

# PESTAÑAS
if es_admin:
    tab_personal, tab_asistencia, tab_visual, tab_admin = st.tabs(["👥 GESTIONAR PERSONAL", "⚡ TOMAR ASISTENCIA", "📈 DASHBOARD", "🔐 ADMINISTRAR"])
else:
    tab_personal, tab_asistencia, tab_visual = st.tabs(["👥 MI EQUIPO", "⚡ TOMAR ASISTENCIA", "📊 MI DASHBOARD"])

# 1. GESTIÓN
with tab_personal:
    if not es_admin and not en_horario: st.error("⛔ Fuera de horario.")
    else:
        st.header("Base de Datos")
        eg = st.selectbox("Equipo:", equipos_disponibles, key="sg") if es_admin else usuario_actual
        if eg:
            df_db = cargar_csv_inteligente(ARCHIVO_EMPLEADOS, ["Equipo", "Nombre", "Cedula"])
            if not df_db.empty and 'Equipo' in df_db.columns: df_show = df_db[df_db['Equipo'] == eg]
            else: df_show = pd.DataFrame(columns=["Equipo", "Nombre", "Cedula"])
            
            df_show = garantizar_columnas(df_show, ["Nombre", "Cedula"])
            df_show = df_show[["Nombre", "Cedula"]] 
            
            df_edit = st.data_editor(df_show, num_rows="dynamic", use_container_width=True, key="edit_pers")
            if st.button("💾 GUARDAR CAMBIOS"):
                guardar_personal(df_edit, eg)
                st.success("✅ Guardado y Respaldado.")
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
            df_all = cargar_csv_inteligente(ARCHIVO_EMPLEADOS, ["Equipo", "Nombre", "Cedula"])
            if not df_all.empty and 'Equipo' in df_all.columns: df_base = df_all[df_all['Equipo'] == ea]
            else: df_base = pd.DataFrame(columns=["Equipo", "Nombre", "Cedula"])
            df_base = garantizar_columnas(df_base, ["Nombre", "Cedula"])

            df_hist = cargar_csv_inteligente(ARCHIVO_ASISTENCIA, ["Fecha", "Equipo", "Nombre"])
            hechos = []
            if not df_hist.empty and 'Fecha' in df_hist.columns and 'Equipo' in df_hist.columns:
                hechos = df_hist[(df_hist['Fecha'] == fecha) & (df_hist['Equipo'] == ea)]['Nombre'].tolist()
            
            pendientes = df_base[~df_base['Nombre'].isin(hechos)]
            
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
                        to_save = garantizar_columnas(to_save, ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"])
                        guardar_asistencia(to_save)
                        st.success("✅ Guardado.")
                        st.rerun()
                    else: st.warning("Selecciona estados.")
            else:
                if df_base.empty: st.warning(f"No hay empleados en '{ea}'.")
                else: st.success("🎉 Todo gestionado.")

# 3. DASHBOARD MEJORADO
with tab_visual:
    st.header("📊 Dashboard Gerencial")
    df_ver = cargar_csv_inteligente(ARCHIVO_ASISTENCIA, ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"])
    
    if not df_ver.empty and 'Fecha' in df_ver.columns:
        df_ver['Fecha_dt'] = pd.to_datetime(df_ver['Fecha']).dt.date
        
        with st.container():
            c1, c2 = st.columns(2)
            fmin, fmax = df_ver['Fecha_dt'].min(), df_ver['Fecha_dt'].max()
            try: rango = c1.date_input("📅 Periodo:", [fmin, fmax])
            except: rango = [fmin, fmax]
            
            eq_fil = None
            if es_admin:
                equipos_unicos = df_ver['Equipo'].unique() if 'Equipo' in df_ver.columns else []
                eq_fil = c2.multiselect("🏢 Filtrar Equipo:", equipos_unicos)
        
        df_fil = df_ver.copy()
        if len(rango) == 2: df_fil = df_fil[(df_fil['Fecha_dt'] >= rango[0]) & (df_fil['Fecha_dt'] <= rango[1])]
        if not es_admin: 
            if 'Equipo' in df_fil.columns: df_fil = df_fil[df_fil['Equipo'] == usuario_actual]
        elif eq_fil: 
            df_fil = df_fil[df_fil['Equipo'].isin(eq_fil)]
        
        st.divider()

        if not df_fil.empty:
            tot = len(df_fil)
            asi = len(df_fil[df_fil['Estado'] == 'Asiste']) if 'Estado' in df_fil.columns else 0
            tar = len(df_fil[df_fil['Estado'] == 'Llegada tarde']) if 'Estado' in df_fil.columns else 0
            aus = len(df_fil[df_fil['Estado'].isin(['Ausente', 'Incapacidad'])]) if 'Estado' in df_fil.columns else 0
            porc = (asi/tot)*100 if tot > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total", tot, border=True)
            k2.metric("% Cumplimiento", f"{porc:.1f}%", delta=f"{porc-100:.1f}%", border=True)
            k3.metric("Tardes", tar, delta=-tar, delta_color="inverse", border=True)
            k4.metric("Faltas", aus, delta=-aus, delta_color="inverse", border=True)
            
            st.subheader("📈 Análisis")
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.caption("Distribución")
                if 'Estado' in df_fil.columns:
                    st.bar_chart(df_fil['Estado'].value_counts(), color="#29b5e8")
            
            with col_g2:
                st.caption("🚨 Ranking de Novedades (Faltas/Tardes)")
                df_nov = df_fil[df_fil['Estado'].isin(['Llegada tarde', 'Ausente', 'Incapacidad'])]
                if not df_nov.empty and 'Equipo' in df_nov.columns:
                    ranking = df_nov['Equipo'].value_counts()
                    st.bar_chart(ranking, color="#ff4b4b") 
                else: st.success("Sin novedades negativas.")

            st.divider()
            st.subheader("📋 Datos")
            st.dataframe(df_fil, use_container_width=True)
            st.download_button("⬇️ Descargar CSV", df_fil.to_csv(index=False).encode('utf-8'), "reporte.csv", "text/csv")
            
            st.divider()
            with st.expander("👤 Trayectoria Individual"):
                nombres = df_fil['Nombre'].unique() if 'Nombre' in df_fil.columns else []
                col = st.selectbox("Buscar:", nombres)
                if col:
                    dft = df_fil[df_fil['Nombre'] == col]
                    st.bar_chart(dft['Estado'].value_counts())
                    st.dataframe(dft[['Fecha','Estado','Observacion']], use_container_width=True)
            
            with st.expander("📂 Soportes"):
                if 'Soporte' in df_fil.columns:
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
        with st.expander("🔑 CONFIGURACIÓN"):
            dl = []
            for t, d in config_db.items():
                p = d.get('password','') if isinstance(d, dict) else str(d)
                i = d.get('inicio','00:00') if isinstance(d, dict) else '00:00'
                f = d.get('fin','23:59') if isinstance(d, dict) else '23:59'
                try: ti, tf = datetime.strptime(i, "%H:%M").time(), datetime.strptime(f, "%H:%M").time()
                except: ti, tf = time(0,0), time(23,59)
                dl.append({"Usuario/Equipo": t, "Contraseña": p, "Inicio": ti, "Fin": tf})
            res = st.data_editor(pd.DataFrame(dl), column_config={"Inicio":st.column_config.TimeColumn(format="HH:mm"),"Fin":st.column_config.TimeColumn(format="HH:mm")}, num_rows="dynamic")
            if st.button("💾 GUARDAR"):
                new_c = {}
                for _, r in res.iterrows():
                    n = str(r['Usuario/Equipo']).strip()
                    if n: new_c[n] = {"password": str(r['Contraseña']), "inicio": r['Inicio'].strftime("%H:%M") if r['Inicio'] else "00:00", "fin": r['Fin'].strftime("%H:%M") if r['Fin'] else "23:59"}
                guardar_configuracion(new_c)
                st.success("Guardado.")
                st.rerun()
        
        st.divider()
        st.subheader("🛠️ Mantenimiento")
        df_full = cargar_csv_inteligente(ARCHIVO_ASISTENCIA, ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion", "Soporte"])
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
        
        st.divider()
        st.markdown("### 🚑 Recuperación de Desastres")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("🔄 RESTAURAR BASE EMPLEADOS (BACKUP)"):
                if recuperar_desde_backup(ARCHIVO_EMPLEADOS):
                    st.success("Empleados restaurados.")
                    st.rerun()
                else: st.error("No hay backup disponible.")
        with col_b2:
            if st.button("🔄 RESTAURAR HISTORIAL (BACKUP)"):
                if recuperar_desde_backup(ARCHIVO_ASISTENCIA):
                    st.success("Historial restaurado.")
                    st.rerun()
                else: st.error("No hay backup disponible.")
        
        if st.button("🚨 REPARAR ARCHIVOS DAÑADOS (Emergencia)"):
            reparar_base_datos_empleados()
            st.success("Archivos reconstruidos.")
            st.rerun()
