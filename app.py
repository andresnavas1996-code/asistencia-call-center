import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- 1. CONFIGURACIÓN ---
HORA_INICIO = time(0, 0)
HORA_FIN = time(23, 59)
ARCHIVO_ASISTENCIA = 'asistencia_historica.csv'
ARCHIVO_EMPLEADOS = 'base_datos_empleados.csv'

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

# --- 2. FUNCIONES DEL SISTEMA ---

def inicializar_empleados():
    """Crea el archivo maestro si no existe."""
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        datos_lista = []
        for equipo, nombres in EQUIPOS_INICIALES.items():
            for nombre in nombres:
                datos_lista.append({
                    "Equipo": equipo, 
                    "Nombre": nombre, 
                    "Cedula": "" 
                })
        df_base = pd.DataFrame(datos_lista)
        # Guardamos asegurando que todo sea texto
        df_base.to_csv(ARCHIVO_EMPLEADOS, index=False)

def cargar_empleados(equipo_filtro):
    """Carga empleados y limpia los valores nulos (None)."""
    if not os.path.exists(ARCHIVO_EMPLEADOS):
        inicializar_empleados()
    
    # keep_default_na=False evita que los espacios vacíos se vuelvan NaN/None
    df_todos = pd.read_csv(ARCHIVO_EMPLEADOS, dtype=str, keep_default_na=False)
    
    # Filtramos por equipo
    df_equipo = df_todos[df_todos['Equipo'] == equipo_filtro].copy()
    return df_equipo

def actualizar_base_empleados(df_nuevos_datos, equipo_actual):
    """Guarda tanto gente nueva como ediciones a los antiguos."""
    df_db = pd.read_csv(ARCHIVO_EMPLEADOS, dtype=str, keep_default_na=False)
    
    cambios = False
    for index, row in df_nuevos_datos.iterrows():
        nombre = str(row['Nombre']).strip()
        cedula = str(row['Cedula']).strip()
        
        # Filtro para encontrar si la persona ya existe en la base de datos
        mask = (df_db['Nombre'] == nombre) & (df_db['Equipo'] == equipo_actual)
        
        if mask.any():
            # CASO 1: LA PERSONA EXISTE -> ACTUALIZAMOS SU CÉDULA
            # Solo actualizamos si la cédula cambió para no reescribir por gusto
            cedula_actual = df_db.loc[mask, 'Cedula'].values[0]
            if cedula != cedula_actual:
                df_db.loc[mask, 'Cedula'] = cedula
                cambios = True
        elif nombre and nombre != "nan":
            # CASO 2: LA PERSONA NO EXISTE -> LA CREAMOS
            nuevo = pd.DataFrame([{
                "Equipo": equipo_actual, 
                "Nombre": nombre, 
                "Cedula": cedula
            }])
            df_db = pd.concat([df_db, nuevo], ignore_index=True)
            cambios = True
            
    if cambios:
        df_db.to_csv(ARCHIVO_EMPLEADOS, index=False)

def guardar_asistencia_diaria(df_nuevo):
    if os.path.exists(ARCHIVO_ASISTENCIA):
        df_historico = pd.read_csv(ARCHIVO_ASISTENCIA, dtype=str, keep_default_na=False)
    else:
        df_historico = pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion"])
        
    df_final = pd.concat([df_historico, df_nuevo], ignore_index=True)
    df_final.to_csv(ARCHIVO_ASISTENCIA, index=False)

# --- 3. INTERFAZ GRÁFICA ---
st.set_page_config(page_title="Asistencia Call Center", layout="wide")
st.title("📋 Malla de Asistencia - Base de Datos Dinámica")

# Asegurar DB
inicializar_empleados()

tab_registro, tab_reporte = st.tabs(["⚡ Registrar Asistencia", "📊 Dashboard"])

with tab_registro:
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        lista_equipos = list(EQUIPOS_INICIALES.keys())
        
        col_sel, _ = st.columns([1, 2])
        with col_sel:
            equipo_sel = st.selectbox("Selecciona tu Equipo:", lista_equipos)
            
        st.info("💡 Ahora sí: Si editas una Cédula o agregas a alguien, el sistema lo recordará.")
        
        # 1. Cargar Base de Datos
        df_empleados = cargar_empleados(equipo_sel)
        
        # 2. Preparar tabla (Rellenar con valores por defecto para hoy)
        df_input = df_empleados[['Nombre', 'Cedula']].copy()
        df_input['Estado'] = "Presente"
        df_input['Observacion'] = ""
        
        # 3. Editor de Datos
        df_editado = st.data_editor(
            df_input,
            column_config={
                "Nombre": st.column_config.TextColumn("Nombre Agente", required=True),
                "Cedula": st.column_config.TextColumn("Cédula / ID", required=True),
                "Estado": st.column_config.SelectboxColumn("Estado", options=["Presente", "Ausente", "Tarde", "Licencia", "Vacaciones"], required=True),
                "Observacion": st.column_config.TextColumn("Observación")
            },
            hide_index=True,
            num_rows="dynamic", 
            use_container_width=True,
            key=f"editor_{equipo_sel}" # Clave única para que no se trabe al cambiar de equipo
        )
        
        # 4. Guardar
        if st.button("💾 Guardar Todo"):
            if not df_editado.empty:
                # A) Actualizar Base de Datos (Nuevos y Ediciones)
                actualizar_base_empleados(df_editado, equipo_sel)
                
                # B) Guardar Asistencia del día
                df_final = df_editado.copy()
                df_final["Fecha"] = datetime.now().strftime("%Y-%m-%d")
                df_final["Equipo"] = equipo_sel
                
                cols = ["Fecha", "Equipo", "Nombre", "Cedula", "Estado", "Observacion"]
                guardar_asistencia_diaria(df_final[cols])
                
                st.toast(f"✅ ¡Guardado! Base de datos de {equipo_sel} actualizada.")
                
                # Truco para recargar la tabla y ver los cambios confirmados
                st.rerun() 
            else:
                st.warning("La tabla está vacía.")
    else:
        st.error(f"⛔ Sistema Cerrado ({HORA_INICIO} - {HORA_FIN})")

with tab_reporte:
    st.header("Histórico")
    if os.path.exists(ARCHIVO_ASISTENCIA):
        df = pd.read_csv(ARCHIVO_ASISTENCIA)
        st.metric("Registros Totales", len(df))
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay datos aún.")
