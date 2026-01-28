# ... (El inicio del código con los imports y EQUIPOS sigue igual, no lo toques) ...

# --- PEGA ESTO REEMPLAZANDO SOLO LA PARTE DE "tab_asistencia" ---
with tab_asistencia:
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        st.success(f"Sistema ABIERTO. Hora actual: {ahora.strftime('%H:%M')}")
        
        col_sel, col_info = st.columns([1, 2])
        with col_sel:
            equipo_sel = st.selectbox("Selecciona tu Equipo:", list(EQUIPOS.keys()))
        
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        st.write(f"### 👥 Gestionando: {equipo_sel}")
        st.info("💡 Tip: Usa la fila vacía al final para agregar personas nuevas.")
        
        # 1. Preparamos los datos, pero SOLO mostramos lo necesario para editar
        datos_equipo = []
        for persona in EQUIPOS[equipo_sel]:
            datos_equipo.append({
                # No incluimos Fecha ni Equipo aquí, se agregan al final
                "Nombre": persona,
                "Estado": "Presente", 
                "Observacion": ""
            })
        
        df_input = pd.DataFrame(datos_equipo)
        
        # 2. El Editor (Sin columnas estorbosas)
        df_editado = st.data_editor(
            df_input,
            column_config={
                "Nombre": st.column_config.TextColumn("Nombre del Agente", required=True),
                "Estado": st.column_config.SelectboxColumn(
                    "Estado",
                    options=["Presente", "Ausente", "Tarde", "Licencia", "Vacaciones"],
                    required=True
                ),
                "Observacion": st.column_config.TextColumn("Observación")
            },
            hide_index=True,
            num_rows="dynamic", # Esto permite agregar filas nuevas sin error
            use_container_width=True
        )
        
        # 3. El Botón de Guardado (Aquí ocurre la magia del auto-llenado)
        if st.button("💾 Guardar Asistencia"):
            if not df_editado.empty:
                # AQUÍ ES DONDE SE AUTO-LLENAN LAS COLUMNAS FALTANTES
                df_a_guardar = df_editado.copy()
                df_a_guardar["Fecha"] = fecha_hoy      # Se pone la fecha de hoy a TODOS
                df_a_guardar["Equipo"] = equipo_sel    # Se pone el equipo actual a TODOS
                
                # Reordenamos las columnas para que queden bonitas en el Excel
                df_a_guardar = df_a_guardar[["Fecha", "Equipo", "Nombre", "Estado", "Observacion"]]
                
                guardar_asistencia(df_a_guardar)
                st
