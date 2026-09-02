import datetime
import requests
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE TELEGRAM ---
# Crear tu bot en Telegram toma 2 minutos hablando con @BotFather
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "8767332293:AAHAtApyDSXzJl9RiecSjYuHPHNTCxLS29w")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "Tde_Carmen_bot")

def enviar_notificacion_telegram(incidencia_id, tutor, aula, elemento, prioridad, descripcion):
    """Envía un mensaje instantáneo al móvil del coordinador TDE."""
    mensaje = (
        f"🚨 *NUEVA INCIDENCIA TDE #{incidencia_id}*\n\n"
        f"👤 *Docente:* {tutor}\n"
        f"🏫 *Aula/Lugar:* {aula}\n"
        f"💻 *Elemento:* {elemento}\n"
        f"⚠️ *Urgencia:* {prioridad}\n"
        f"📝 *Detalle:* {descripcion}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        st.warning(f"No se pudo enviar la alerta de Telegram: {e}")

# --- CONFIGURACIÓN PÁGINA ---
st.set_page_config(page_title="Gestión Incidencias TDE", page_icon="💻", layout="centered")

# Conexión nativa de Streamlit a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_incidencias():
    # Lee la primera pestaña de tu hoja de Google Sheets
    return conn.read(ttl=0)  # ttl=0 para no usar caché y ver cambios en tiempo real

# --- INTERFAZ ---
st.title("💻 Centro CEIP - Incidencias TDE")
st.caption("Comunicación directa con la Coordinación TDE")

tab1, tab2 = st.tabs(["📝 Reportar Incidencia", "⚙️ Panel Coordinador"])

with tab1:
    st.markdown("Completa los datos para notificar tu avería:")
    
    with st.form(key="form_incidencia", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tutor = st.text_input("Nombre y Apellidos *")
            edificio = st.selectbox("Edificio / Etapa *", ["Infantil - Edificio 2", "Primaria - Edificio 2", "Sala_Profesores - Edificio 2", "Aula STEAM - Edificio 2", "Equipo_Directivo / Edificio 1", "Administración - Edificio 1"])
            aula = st.selectbox("Aula / Espacio *", [
                "3 años", "4 años", "5 años", "1º", "2º", "3º", "4º", "5º", "6ºA", "6ºB", "Aula ZTS", "Aula PT", "Aula STEAM", "Aula Informática", "Sala Profesores", "Biblioteca", "Secretaría"
            ])
        with col2:
            elemento = st.selectbox("Elemento o Dispositivo *", [
                "PDI (Pizarra Digital Interactiva)/ Proyector", "Ordenador Aula", "Portátil Docente",
                "Wi-Fi / Red ", "Impresora / Escáner", "Audio / Altavoces",
                "Plataforma Digital (Séneca, Moodle, Google, Teams)", "Otro"
            ])
            tipo_averia = st.selectbox("Tipo de problema *", [
                "No enciende / Eléctrico", "Fallo de Internet", "Pantalla / Calibración",
                "Sin sonido", "Periférico roto", "Software / S.O. desconfigurado", "Asistencia técnica"
            ])
            prioridad = st.select_slider(
                "Nivel de urgencia *",
                options=["Baja", "Media", "Alta"]
            )
            
        descripcion = st.text_area("Descripción detallada *")
        btn_enviar = st.form_submit_button("🚀 Registrar Incidencia", type="primary")

        if btn_enviar:
            if not tutor or not descripcion:
                st.error("⚠️ Nombre y descripción son obligatorios.")
            else:
                df_actual = cargar_incidencias()
                nuevo_id = 1 if df_actual.empty else int(df_actual["ID"].max()) + 1
                
                nueva_fila = pd.DataFrame([{
                    "ID": nuevo_id,
                    "Fecha_Hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Tutor_Nombre": tutor,
                    "Edificio": edificio,
                    "Aula": aula,
                    "Elemento": elemento,
                    "Tipo_Incidencia": tipo_averia,
                    "Prioridad": prioridad,
                    "Descripcion": descripcion,
                    "Estado": "Pendiente"
                }])
                
                # Unir e integrar en Google Sheets
                df_actualizado = pd.concat([df_actual, nueva_fila], ignore_index=True)
                conn.update(data=df_actualizado)
                
                # Enviar notificación inmediata a Telegram
                enviar_notificacion_telegram(nuevo_id, tutor, aula, elemento, prioridad, descripcion)
                
                st.success(f"✅ ¡Registrada con éxito! Código: **#{nuevo_id}**")

with tab2:
    st.subheader("📊 Panel de Control TDE")
    password = st.text_input("Contraseña TDE", type="password")
    
    if password == "tde2026":
        df = cargar_incidencias()
        if not df.empty:
            st.metric("Total de incidencias", len(df))
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Sin incidencias registradas.")