import datetime
import pandas as pd
import requests
import streamlit as st
from supabase import create_client, Client

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
            
            # Botón para descargar el reporte en CSV
            csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Reporte Filtrado (CSV)",
                data=csv_data,
                file_name=f"incidencias_{filtro_estado}_{datetime.date.today()}.csv",
                mime="text/csv",
            )
    elif password:
        st.error("Contraseña incorrecta.")