import streamlit as st
import pandas as pd
from datetime import datetime, time
import os
import pytz 
import json

# --- 1. CONFIGURACIÓN ---
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
        hora_co = obtener_hora_colombia().strftime("%H:%M")
        st.caption(f"🕒 Hora CO: {hora_co}")
    except: pass
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
                        st.success("✅ Guardado.")
                        st.rerun()
                    else:
                        st.warning("Selecciona estados.")
            else:
                st.success("🎉 Al día.")

# 3. DASHBOARD (MEJORADO)
with tab_visual:
    st.header("📊 Dashboard de Gestión")
    df_ver = cargar_csv(ARCHIVO_ASISTENCIA)
    
    if not df_ver.empty:
        # Convertimos fecha a datetime para filtrar
        df_ver['Fecha_dt'] = pd.to_datetime(df_ver['Fecha']).dt.date
        
        # Filtros
        c1, c2 = st.columns(2)
        with c1:
            # FILTRO DE FECHAS MEJORADO
            fecha_min = df_ver['Fecha_dt'].min()
            fecha_max = df_ver['Fecha_dt'].max()
            try:
                rango_fechas = st.date_input("📅 Rango de Fechas:", [fecha_min, fecha_max])
            except:
                rango_fechas = [fecha_min, fecha_max] # Fallback
                
        with c2:
            equipos_filtro = st.multiselect("Equipo:", df_ver['Equipo'].unique()) if es_admin else None
            
        # Aplicar Filtros
        df_fil = df_ver.copy()
        
        if len(rango_fechas) == 2:
            df_fil = df_fil[
                (df_fil['Fecha_dt'] >= rango_fechas[0]) & 
                (df_fil['Fecha_dt'] <= rango_fechas[1])
            ]
            
        if not es_admin: 
            df_fil = df_fil[df_fil['Equipo'] == usuario_actual]
        elif equipos_filtro: 
            df_fil = df_fil[df_fil['Equipo'].isin(equipos_filtro)]
        
        # KPIs Globales
        if not df_fil.empty:
            total = len(df_fil)
            asistencia = len(df_fil[df_fil['Estado'] == 'Asiste'])
            tardanza = len(df_fil[df_fil['Estado'] == 'Llegada tarde'])
            ausencia = len(df_fil[df_fil['Estado'].isin(['Ausente', 'Incapacidad'])])
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Registros", total)
            k2.metric("% Asistencia", f"{(asistencia/total)*100:.1f}%")
            k3.metric("Llegadas Tarde", tardanza, delta_color="inverse")
            k4.metric("Ausencias", ausencia, delta_color="inverse")
            
            st.divider()
            
            # Tabla y Exportación
            st.subheader("📋 Detalle Filtrado")
            st.dataframe(df_fil, use_container_width=True)
            
            # BOTÓN DE DESCARGA
            csv = df_fil.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Descargar Reporte en Excel (CSV)",
                data=csv,
                file_name="reporte_asistencia.csv",
                mime='text/csv'
            )
            
            # SECCIÓN: TRAYECTORIA INDIVIDUAL
            st.divider()
            st.subheader("👤 Trayectoria del Colaborador")
            with st.expander("🔍 Consultar Trayectoria Individual"):
                colab_list = df_fil['Nombre'].unique()
                seleccion_colab = st.selectbox("Seleccionar Colaborador:", colab_list)
                
                if seleccion_colab:
                    df_trayectoria = df_fil[df_fil['Nombre'] == seleccion_colab]
                    
                    # KPIs Personales
                    t_p = len(df_trayectoria)
                    t_tarde = len(df_trayectoria[df_trayectoria['Estado'] == 'Llegada tarde'])
                    t_aus = len(df_trayectoria[df_trayectoria['Estado'].isin(['Ausente', 'Incapacidad'])])
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Días Registrados", t_p)
                    m2.metric("Veces Tarde", t_tarde, delta_color="inverse")
                    m3.metric("Incapacidades/Faltas", t_aus, delta_color="inverse")
                    
                    st.write("**Historial de Estados:**")
                    st.bar_chart(df_trayectoria['Estado'].value_counts())
                    st.dataframe(df_trayectoria[['Fecha', 'Estado', 'Observacion']], use_container_width=True)

            # VISOR
            st.divider()
            st.subheader("📂 Visor de Soportes")
            con_soporte = df_fil[df_fil['Soporte'].notna() & (df_fil['Soporte'].astype(str).str.len() > 5)]
            if not con_soporte.empty:
                sel = st.selectbox("Seleccionar registro:", con_soporte['Nombre'] + " - " + con_soporte['Fecha'], key="visor_sel")
                if sel:
                    row = con_soporte[con_soporte['Nombre'] + " - " + con_soporte['Fecha'] == sel].iloc[0]
                    ruta = row['Soporte']
                    if os.path.exists(ruta):
                        with open(ruta, "rb") as file:
                            st.download_button(label="⬇️ DESCARGAR SOPORTE", data=file, file_name=os.path.basename(ruta))
                        if ruta.endswith(".pdf"): st.info("📄 Documento PDF disponible para descarga.")
                        else: st.image(ruta, caption="Vista previa", width=400)
                    else: st.error("❌ Archivo no encontrado.")
            else:
                st.info("No hay soportes en la selección.")
        else:
            st.warning("No hay datos en este rango de fechas.")
    else:
        st.info("Sin datos históricos.")

# 4. ADMIN (CONFIG Y CORRECCIONES)
if es_admin:
    with tab_admin:
        st.header("🔐 Admin")
        with st.expander("🔑 CONFIGURACIÓN DE EQUIPOS"):
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
        st.subheader("🛠️ Corregir Historial")
        df_full = cargar_csv(ARCHIVO_ASISTENCIA)
        if not df_full.empty:
            df_full.insert(0, "Borrar", False)
            edited_full = st.data_editor(
                df_full,
                column_config={
                    "Borrar": st.column_config.CheckboxColumn(default=False),
                    "Fecha": st.column_config.Column(disabled=True),
                    "Equipo": st.column_config.Column(disabled=True),
                    "Nombre": st.column_config.Column(disabled=True),
                    "Estado": st.column_config.SelectboxColumn(options=["Asiste", "Ausente", "Llegada tarde", "Incapacidad", "Vacaciones"]),
                    "Soporte": st.column_config.Column(disabled=True)
                },
                hide_index=True, use_container_width=True, key="edit_full_admin"
            )
            
            if st.button("💾 APLICAR CORRECCIONES"):
                final_df = edited_full[edited_full["Borrar"] == False]
                sobrescribir_asistencia_completa(final_df)
                st.success("✅ Actualizado.")
                st.rerun()
                
            with st.expander("☢️ BORRAR TODO"):
                if st.button("🔴 CONFIRMAR BORRADO"):
                    borrar_historial_completo()
                    st.rerun()
