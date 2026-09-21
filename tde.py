import datetime
import pandas as pd
import requests
import streamlit as st
from supabase import create_client, Client

import io
import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generar_pdf_incidencias(df):
    """Genera un archivo PDF horizontal con las incidencias formateadas para el equipo directivo."""
    buffer = io.BytesIO()
    
    # Documento en formato A4 Horizontal (Landscape) para dar cabida a todas las columnas
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )
    
    elementos = []
    styles = getSampleStyleSheet()
    
    # --- ESTILOS PERSONALIZADOS ---
    titulo_style = ParagraphStyle(
        'TituloInforme',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E3A8A'),  # Azul corporativo
        spaceAfter=6
    )
    
    subtitulo_style = ParagraphStyle(
        'SubtituloInforme',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=15
    )
    
    celda_header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        alignment=1  # Centrado
    )
    
    celda_body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1F2937')
    )

    # --- CABECERA Y RESUMEN EJECUTIVO ---
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    elementos.append(Paragraph("Informe de Actuaciones e Incidencias TDE", titulo_style))
    
    total_incidencias = len(df)
    pendientes = len(df[df['estado'] == 'Pendiente']) if 'estado' in df.columns else 0
    resueltas = len(df[df['estado'] == 'Resuelta']) if 'estado' in df.columns else 0
    
    resumen_texto = f"<b>Fecha de generación:</b> {fecha_hoy} | <b>Total de incidencias:</b> {total_incidencias} | <b>Pendientes:</b> {pendientes} | <b>Resueltas:</b> {resueltas}"
    elementos.append(Paragraph(resumen_texto, subtitulo_style))
    elementos.append(Spacer(1, 10))
    
    # --- CONSTRUCCIÓN DE LA TABLA ---
    # Columnas a mostrar en el informe
    columnas_deseadas = ['id', 'fecha_hora', 'edificio', 'aula', 'elemento', 'tipo', 'prioridad', 'estado', 'descripcion']
    headers_limpios = ['ID', 'Fecha', 'Edificio', 'Aula', 'Elemento', 'Tipo', 'Prioridad', 'Estado', 'Descripción']
    
    # Filtrar solo las columnas que existan en el DataFrame
    cols_existentes = [c for c in columnas_deseadas if c in df.columns]
    
    # Fila de cabecera
    data_tabla = [[Paragraph(h, celda_header_style) for h in headers_limpios]]
    
    # Filas de datos
    for _, row in df.iterrows():
        fila = []
        for col in cols_existentes:
            val = str(row[col]) if row[col] is not None else ""
            fila.append(Paragraph(val, celda_body_style))
        data_tabla.append(fila)

    # Anchos de columna optimizados para A4 Horizontal (~780pt ancho utilizable)
    col_widths = [30, 80, 60, 50, 80, 80, 65, 65, 270]

    tabla = Table(data_tabla, colWidths=col_widths, repeatRows=1)
    
    # Estilo visual de la tabla (colores intercalados, bordes finos, cabecera azul)
    estilo_tabla = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ])
    
    # Añadir filas de fondo alternado (efecto cebra)
    for i in range(1, len(data_tabla)):
        if i % 2 == 0:
            estilo_tabla.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F9FAFB'))
            
    tabla.setStyle(estilo_tabla)
    elementos.append(tabla)
    
    # Construir PDF
    doc.build(elementos)
    buffer.seek(0)
    return buffer
    
# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Gestión de Incidencias TDE",
    page_icon="💻",
    layout="centered"
)

# --- CONEXIÓN A SUPABASE ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("❌ Faltan las credenciales SUPABASE_URL o SUPABASE_KEY en los secretos de Streamlit Cloud.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# --- FUNCIONES DE BASE DE DATOS (SUPABASE) ---
def guardar_incidencia_supabase(tutor, edificio, aula, elemento, tipo, prioridad, descripcion):
    """Inserta una nueva incidencia en Supabase y retorna el ID asignado."""
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    datos = {
        "fecha_hora": fecha_actual,
        "tutor": tutor,
        "edificio": edificio,
        "aula": aula,
        "elemento": elemento,
        "tipo": tipo,
        "prioridad": prioridad,
        "descripcion": descripcion,
        "estado": "Pendiente"
    }
    
    try:
        respuesta = supabase.table("incidencias").insert(datos).execute()
        if respuesta.data:
            return respuesta.data[0]["id"]
        return None
    except Exception as e:
        st.error(f"⚠️ Error de conexión con Supabase: {e}")
        return None
        
def cargar_incidencias_supabase():
    """Carga todas las incidencias de Supabase en un DataFrame de Pandas."""
    try:
        respuesta = supabase.table("incidencias").select("*").order("id", desc=True).execute()
        return pd.DataFrame(respuesta.data)
    except Exception as e:
        st.error(f"❌ Error al cargar incidencias de Supabase: {e}")
        return pd.DataFrame()

def actualizar_estado_incidencia(incidencia_id, nuevo_estado):
    """Actualiza el estado de una incidencia en Supabase."""
    try:
        supabase.table("incidencias").update({"estado": nuevo_estado}).eq("id", incidencia_id).execute()
    except Exception as e:
        st.error(f"❌ Error al actualizar la incidencia #{incidencia_id}: {e}")

# --- CONFIGURACIÓN DE TELEGRAM ---
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

def enviar_notificacion_telegram(incidencia_id, tutor, aula, elemento, prioridad, descripcion):
    """Envía un mensaje instantáneo de alerta al móvil del coordinador TDE."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        st.warning("⚠️ Las credenciales de Telegram no están configuradas correctamente en los secretos.")
        return

    mensaje = (
        f"🚨 *NUEVA INCIDENCIA TDE #{incidencia_id}*\n\n"
        f"👤 *Docente:* {tutor}\n"
        f"🏫 *Aula/Espacio:* {aula}\n"
        f"💻 *Elemento:* {elemento}\n"
        f"⚠️ *Urgencia:* {prioridad}\n"
        f"📝 *Detalle:* {descripcion}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        res_json = r.json()
        if not res_json.get("ok"):
            st.error(f"❌ Telegram rechazó el mensaje: {res_json.get('description')}")
    except Exception as e:
        st.error(f"⚠️ Fallo de red al contactar con Telegram: {e}")

# --- FUNCIONES DE BASE DE DATOS (SUPABASE) ---
def guardar_incidencia_supabase(tutor, edificio, aula, elemento, tipo, prioridad, descripcion):
    """Inserta una nueva incidencia en Supabase y retorna el ID asignado."""
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    datos = {
        "fecha_hora": fecha_actual,
        "tutor": tutor,
        "edificio": edificio,
        "aula": aula,
        "elemento": elemento,
        "tipo": tipo,
        "prioridad": prioridad,
        "descripcion": descripcion,
        "estado": "Pendiente"
    }
    
    respuesta = supabase.table("incidencias").insert(datos).execute()
    nuevo_id = respuesta.data[0]["id"]
    return nuevo_id

def cargar_incidencias_supabase():
    """Carga todas las incidencias de Supabase en un DataFrame de Pandas."""
    respuesta = supabase.table("incidencias").select("*").order("id", desc=True).execute()
    return pd.DataFrame(respuesta.data)

def actualizar_estado_incidencia(incidencia_id, nuevo_estado):
    """Actualiza el estado de una incidencia en Supabase."""
    supabase.table("incidencias").update({"estado": nuevo_estado}).eq("id", incidencia_id).execute()

# --- INTERFAZ DE USUARIO ---
st.title("💻 CEIP Virgen del Carmen (Alcaudete) - Incidencias TDE")
st.caption("Punto de comunicación directa con el Coordinador de Transformación Digital Educativa.")

tab1, tab2 = st.tabs(["📝 Reportar Incidencia", "⚙️ Panel Coordinación TDE"])

# --- TAB 1: FORMULARIO DOCENTES ---
with tab1:
    st.markdown("Por favor, completa los siguientes datos para notificar tu avería o consulta:")
    
    with st.form(key="form_incidencia", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            tutor = st.text_input("Nombre y Apellidos del Tutor/a *", placeholder="Ej. María García")
            edificio = st.selectbox("Edificio / Etapa *", [
                "Infantil - Primaria", "Equipo Directivo - Administración"
            ])
            aula = st.selectbox("Aula / Espacio *", [
                "3 años", "4 años", "5 años ",
                "1º", "2º", "3º", "4º", "5º", "6ºA", "6ºB", "Aula PT", "Aula ZTS", "Aula STEAM", "Sala Profesores", "Biblioteca"
            ])

        with col2:
            elemento = st.selectbox("Elemento o Dispositivo *", [
                "PDI (Pantalla Digital Interactiva)",
                "Ordenador de Aula (Sobremesa)",
                "Portátil del Docente",
                "Conexión Wi-Fi / Red Cable",
                "Impresora / Escáner",
                "Sistemas de Audio / Altavoces",
                "Plataforma Digital (Séneca / Moodle / GSuite / Microsoft)",
                "Otro dispositivo"
            ])
            
            tipo = st.selectbox("Tipo de problema *", [
                "No enciende / Problema eléctrico",
                "Fallo de conexión a Internet",
                "Imagen / Pantalla no se ve o no calibra",
                "Sin sonido",
                "Periférico roto (ratón, teclado, cable, mando)",
                "Software / Sistema Operativo desconfigurado",
                "Solicitud de nuevo software o recurso",
                "Duda / Asistencia técnica"
            ])
            
            prioridad = st.select_slider(
                "Nivel de urgencia *",
                options=["Baja (No impide dar clase)", "Media (Se puede trabajar con alternativa)", "Alta (Imposible impartir clase)"],
                value="Media (Se puede trabajar con alternativa)"
            )

        descripcion = st.text_area("Descripción detallada del problema *", placeholder="Describe brevemente qué ocurre...")
        
        btn_enviar = st.form_submit_button("🚀 Registrar Incidencia", type="primary")

        if btn_enviar:
            if not tutor or not descripcion:
                st.error("⚠️ Por favor, rellena al menos tu nombre y la descripción del problema.")
            else:
                # 1. Guardar en Supabase
                res_id = guardar_incidencia_supabase(tutor, edificio, aula, elemento, tipo, prioridad, descripcion)
                
                # 2. Notificar por Telegram
                enviar_notificacion_telegram(res_id, tutor, aula, elemento, prioridad, descripcion)
                
                st.success(f"✅ ¡Incidencia registrada con éxito! Código de referencia: **#{res_id}**")
                st.info("El coordinador TDE ha recibido la alerta y responderá a la mayor brevedad.")

# --- TAB 2: PANEL COORDINADOR ---
with tab2:
    st.subheader("📊 Histórico y Gestión de Incidencias")
    
    password = st.text_input("Contraseña de Coordinador TDE", type="password")
    
    if password == "tde2026":
        df = cargar_incidencias_supabase()
        
        if df.empty:
            st.info("No hay incidencias registradas por el momento.")
        else:
            # 1. TARJETAS DE MÉTRICAS RÁPIDAS
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Total Registradas", len(df))
            col_m2.metric("🔴 Pendientes", len(df[df["estado"] == "Pendiente"]))
            col_m3.metric("🟡 En Proceso", len(df[df["estado"] == "En proceso"]))
            col_m4.metric("🟢 Resueltas", len(df[df["estado"] == "Resuelta"]))
            
            st.markdown("---")
            
            # 2. SECCIÓN PARA CAMBIAR EL ESTADO DE UNA INCIDENCIA
            st.markdown("### 🛠️ Actualizar Estado de una Incidencia")
            c_col1, c_col2, c_col3 = st.columns([1, 1, 1])
            
            with c_col1:
                incidencia_sel = st.selectbox("Seleccionar ID Incidencia", df["id"].tolist())
            with c_col2:
                nuevo_estado = st.selectbox("Nuevo Estado", ["Pendiente", "En proceso", "Resuelta"])
            with c_col3:
                st.write("")
                st.write("")
                if st.button("💾 Guardar Cambio"):
                    actualizar_estado_incidencia(incidencia_sel, nuevo_estado)
                    st.success(f"¡Incidencia #{incidencia_sel} actualizada a '{nuevo_estado}'!")
                    st.rerun()

            st.markdown("---")
            
            # 3. FILTRO DE VISUALIZACIÓN
            st.markdown("### 📋 Listado de Incidencias")
            filtro_estado = st.radio(
                "Filtrar por estado:",
                ["Todas", "Pendientes", "En proceso", "Resueltas"],
                horizontal=True
            )
            
            if filtro_estado == "Pendientes":
                df_filtrado = df[df["estado"] == "Pendiente"]
            elif filtro_estado == "En proceso":
                df_filtrado = df[df["estado"] == "En proceso"]
            elif filtro_estado == "Resueltas":
                df_filtrado = df[df["estado"] == "Resuelta"]
            else:
                df_filtrado = df

            st.dataframe(df_filtrado, use_container_width=True)
            
            # Cargar incidencias desde Supabase
            df_incidencias = cargar_incidencias_supabase()

            if not df_incidencias.empty:
                st.dataframe(df_incidencias, use_container_width=True)
    
                col1, col2 = st.columns(2)
    
                # 1. Descarga en CSV (mantener como alternativa)
                with col1:
                    csv_data = df_incidencias.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📄 Descargar como CSV",
                        data=csv_data,
                        file_name=f"incidencias_{datetime.date.today()}.csv",
                        mime="text/csv"
                    )
        
                # 2. NUEVO: Descarga en PDF Presentable
                with col2:
                    pdf_buffer = generar_pdf_incidencias(df_incidencias)
                    st.download_button(
                        label="📕 Descargar Informe PDF Directiva",
                        data=pdf_buffer,
                        file_name=f"Informe_TDE_{datetime.date.today()}.pdf",
                        mime="application/pdf"
                    )
            else:
                st.info("No hay incidencias registradas para generar el informe.")
        
            