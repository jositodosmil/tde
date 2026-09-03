import datetime
import os
import sqlite3
import pandas as pd
import requests
import streamlit as st

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Gestión de Incidencias TDE",
    page_icon="💻",
    layout="centered"
)

DB_FILE = "incidencias.db"

# --- CONFIGURACIÓN DE TELEGRAM ---
# Lee de secretos o usa los valores directamente si estás en local
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "8767332293:AAHAtApyDSXzJl9RiecSjYuHPHNTCxLS29w")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "Tde_Carmen_bot")

def enviar_notificacion_telegram(incidencia_id, tutor, aula, elemento, prioridad, descripcion):
    """Envía un mensaje instantáneo de alerta al móvil del coordinador TDE."""
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
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        st.warning(f"⚠️ Incidencia guardada, pero falló la alerta de Telegram: {e}")

# --- GESTIÓN DE BASE DE DATOS SQLITE ---
def init_db():
    """Crea la tabla de base de datos si no existe."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT,
            tutor TEXT,
            edificio TEXT,
            aula TEXT,
            elemento TEXT,
            tipo TEXT,
            prioridad TEXT,
            descripcion TEXT,
            estado TEXT
        )
    ''')
    conn.commit()
    conn.close()

def guardar_incidencia_sqlite(tutor, edificio, aula, elemento, tipo, prioridad, descripcion):
    """Inserta un nuevo registro en SQLite y retorna el ID asignado."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cursor.execute('''
        INSERT INTO incidencias (fecha_hora, tutor, edificio, aula, elemento, tipo, prioridad, descripcion, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente')
    ''', (fecha_actual, tutor, edificio, aula, elemento, tipo, prioridad, descripcion))
    
    nuevo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return nuevo_id

def cargar_incidencias_sqlite():
    """Carga todas las incidencias guardadas en un dataframe de Pandas."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM incidencias ORDER BY id DESC", conn)
    conn.close()
    return df

def actualizar_estado_incidencia(incidencia_id, nuevo_estado):
    """Permite al coordinador cambiar el estado de la incidencia."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE incidencias SET estado = ? WHERE id = ?", (nuevo_estado, incidencia_id))
    conn.commit()
    conn.close()

# Inicializar la base de datos al arrancar
init_db()

# --- INTERFAZ DE USUARIO ---
st.title("💻 Centro CEIP - Incidencias TDE")
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
                "Infantil", "Primaria - Edificio A", "Primaria - Edificio B", "Especiales / Administración"
            ])
            aula = st.selectbox("Aula / Espacio *", [
                "3 años A", "3 años B", "4 años A", "4 años B", "5 años A", "5 años B",
                "1ºA", "1ºB", "2ºA", "2ºB", "3ºA", "3ºB", "4ºA", "4ºB", "5ºA", "5ºB", "6ºA", "6ºB",
                "Aula de Informática", "Sala de Profesorado", "Biblioteca", "Gimnasio/Salón de Actos", "Despacho/Secretaría"
            ])

        with col2:
            elemento = st.selectbox("Elemento o Dispositivo *", [
                "PDI / Panel Interactivo / Proyector",
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
                # 1. Guardar en la base de datos SQLite
                res_id = guardar_incidencia_sqlite(tutor, edificio, aula, elemento, tipo, prioridad, descripcion)
                
                # 2. Notificar por Telegram
                enviar_notificacion_telegram(res_id, tutor, aula, elemento, prioridad, descripcion)
                
                st.success(f"✅ ¡Incidencia registrada con éxito! Código de referencia: **#{res_id}**")
                st.info("El coordinador TDE ha recibido la alerta y responderá a la mayor brevedad.")

# --- TAB 2: PANEL COORDINADOR ---
with tab2:
    st.subheader("📊 Histórico y Gestión de Incidencias")
    
    # 1. Se define la variable password con el input del usuario
    password = st.text_input("Contraseña de Coordinador TDE", type="password")
    
    # 2. SE COMPRUEBA DENTRO DEL 'WITH TAB2'
    if password == "tde2026":  # Cambia esta clave si lo deseas
        df = cargar_incidencias_supabase()
        
        if df.empty:
            st.info("No hay incidencias registradas por el momento.")
        else:
            # Métricas rápidas
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total registradas", len(df))
            col_m2.metric("Pendientes", len(df[df["estado"] == "Pendiente"]))
            col_m3.metric("Resueltas", len(df[df["estado"] == "Resuelta"]))
            
            st.markdown("---")
            
            # Gestión del estado
            st.markdown("### 🛠️ Actualizar Estado de Incidencia")
            c_col1, c_col2, c_col3 = st.columns([1, 1, 1])
            with c_col1:
                incidencia_sel = st.selectbox("Seleccionar ID Incidencia", df["id"].tolist())
            with c_col2:
                nuevo_estado = st.selectbox("Nuevo Estado", ["Pendiente", "En proceso", "Resuelta"])
            with c_col3:
                st.write("")
                st.write("")
                if st.button("Guardar Estado"):
                    actualizar_estado_incidencia(incidencia_sel, nuevo_estado)
                    st.success(f"Incidencia #{incidencia_sel} actualizada a '{nuevo_estado}'")
                    st.rerun()

            st.markdown("---")
            st.dataframe(df, use_container_width=True)
            
            # Descargar archivo CSV
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Reporte Completo (CSV/Excel)",
                data=csv_data,
                file_name=f"incidencias_TDE_{datetime.date.today()}.csv",
                mime="text/csv",
            )
    elif password:
        st.error("Contraseña incorrecta.")