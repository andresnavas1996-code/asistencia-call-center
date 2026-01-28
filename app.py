import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- 1. CONFIGURACIÓN DE EQUIPOS ---
EQUIPOS = {
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

# Configuración del horario
HORA_INICIO = time(0, 0)
HORA_FIN = time(23, 59)
ARCHIVO_DATOS = 'asistencia_historica.csv'

# --- 2. FUNCIONES DE CARGA Y GUARDADO ---
def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        return pd.read_csv(ARCHIVO_DATOS)
    else:
        return pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Estado", "Observacion"])

def guardar_asistencia(df_nuevo):
    df_historico = cargar_datos()
    df_final = pd.concat([df_historico, df_nuevo], ignore_index=True)
    df_final.to_csv(ARCHIVO_DATOS, index=False)
    return df_final

# --- 3. INTERFAZ DE USUARIO ---
st.set_page_config(page_title="Control de Asistencia", layout="wide")
st.title("📋 Malla de Asistencia Diaria - Dinámica")

# ESTA
