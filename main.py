import json
import requests
import time
from datetime import datetime
from flask import Flask, request, jsonify
from google import genai
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# CONFIGURACIÓN GLOBAL
# ==========================================
app = Flask(__name__)

VERIFY_TOKEN = ""  # Token para verificar el webhook con Meta (puedes cambiarlo, pero debe coincidir con el que pongas en la configuración del webhook de Meta)
META_TOKEN = ""  # Token de acceso de Meta para enviar mensajes (obtenlo en tu app de Facebook Developers)
PHONE_NUMBER_ID = ""  # ID del número de teléfono de WhatsApp (lo obtienes al configurar tu número en Facebook Developers)

gemini_client = genai.Client(api_key="//gemini api key aqui //")  # Reemplaza con tu API Key de Gemini
groq_client = Groq(api_key="//groq api key aqui //")

# ==========================================
# ☁️ CONEXIÓN A FIREBASE (EL CEREBRO CENTRAL)
# ==========================================
try:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase conectado con éxito!")
except Exception as e:
    print(f"❌ Error al conectar Firebase: {e}. ¿Pusiste el archivo firebase-key.json en la carpeta?")

def guardar_en_firebase(tarea_gemini) -> bool:
    """Convierte el JSON de WhatsApp al formato del Dashboard y lo inyecta a Firebase"""
    # Si la fecha viene vacía o rara, usamos la de hoy en formato YYYY-MM-DD
    fecha_tarea = tarea_gemini.get("fecha")
    if not fecha_tarea or "/" in fecha_tarea:
        fecha_tarea = datetime.now().strftime("%Y-%m-%d")

    nueva_tarea = {
        "id": int(time.time() * 1000), 
        "title": tarea_gemini.get("titulo", "Tarea de WA"),
        "desc": f"📱 Vía WhatsApp: {tarea_gemini.get('descripcion', '')} {tarea_gemini.get('hora', '')}",
        "date": fecha_tarea,
        "color": "green", # Verde para identificar rápido que viene de WhatsApp
        "subtasks": []
    }
    
    try:
        doc_ref = db.collection("usuario").document("mis_tareas")
        # ArrayUnion inyecta la tarea nueva sin borrar las que ya tenías de Telegram o manuales
        doc_ref.set({"lista": firestore.ArrayUnion([nueva_tarea])}, merge=True)
        print(f"☁️ ¡Tarea guardada en la Nube! ({nueva_tarea['title']})")
        return True
    except Exception as e:
        print(f"❌ Error al guardar en la nube: {e}")
        return False

# ==========================================
# MÓDULO: PROCESAR CON GEMINI
# ==========================================
def extraer_datos_tarea(texto_usuario: str) -> dict | None:
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    Eres el motor de un gestor de tareas. Hoy es {fecha_actual}.
    Extrae la info del texto: "{texto_usuario}"
    
    Devuelve ESTRICTAMENTE este JSON (prohibido agregar texto fuera de él):
    {{
        "titulo": "Acción corta",
        "descripcion": "Contexto extra",
        "fecha": "Fecha en formato EXACTO YYYY-MM-DD. (Ejemplo: 2026-03-04). Calcúlala usando la fecha de hoy como referencia",
        "hora": "HH:MM o string vacío"
    }}
    """
    try:
        response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        texto_limpio = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpio)
    except Exception as e:
        print(f"❌ Error Gemini: {e}")
        return None

# ==========================================
# MÓDULOS AUXILIARES
# ==========================================
def enviar_mensaje(destinatario: str, cuerpo: str) -> None:
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {META_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": destinatario, "type": "text", "text": {"body": cuerpo}}
    respuesta = requests.post(url, headers=headers, json=data)
    if respuesta.status_code == 200:
        print(f"✅ Confirmación enviada a {destinatario}")

def normalizar_numero(numero: str) -> str:
    return "52" + numero[3:] if numero.startswith("521") and len(numero) == 13 else numero

def transcribir_audio(ruta_audio: str) -> str | None:
    try:
        with open(ruta_audio, "rb") as archivo:
            transcripcion = groq_client.audio.transcriptions.create(
                file=(ruta_audio, archivo.read()), model="whisper-large-v3", language="es", response_format="text"
            )
        return transcripcion.strip() if isinstance(transcripcion, str) else transcripcion.text.strip()
    except Exception as e:
        print(f"❌ Error Transcripción: {e}")
        return None

def descargar_audio(media_id: str) -> str | None:
    headers = {"Authorization": f"Bearer {META_TOKEN}"}
    respuesta_info = requests.get(f"https://graph.facebook.com/v18.0/{media_id}", headers=headers)
    if respuesta_info.status_code == 200:
        respuesta_audio = requests.get(respuesta_info.json()["url"], headers=headers)
        ruta_local = f"audio_{media_id}.ogg"
        with open(ruta_local, "wb") as f: f.write(respuesta_audio.content)
        return ruta_local
    return None

# ==========================================
# SERVIDOR WEBHOOK (EL QUE FUNCIONÓ)
# ==========================================
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        return "Token inválido", 403

    if request.method == 'POST':
        numero_remitente = None
        try:
            mensaje = request.get_json()['entry'][0]['changes'][0]['value']['messages'][0]
            numero_remitente = normalizar_numero(mensaje['from'])
            texto = mensaje['text']['body'] if mensaje['type'] == 'text' else None
            
            if mensaje['type'] == 'audio':
                ruta = descargar_audio(mensaje['audio']['id'])
                texto = transcribir_audio(ruta) if ruta else None

            if texto:
                tarea = extraer_datos_tarea(texto)
                if tarea:
                    guardado_ok = guardar_en_firebase(tarea) # ☁️ 🔥 LA INYECCIÓN A LA NUBE
                    if guardado_ok:
                        enviar_mensaje(numero_remitente, f"✅ Solicitud completada.\n📌 {tarea.get('titulo')}\n📅 {tarea.get('fecha')}")
                    else:
                        enviar_mensaje(numero_remitente, "❌ Procesé tu solicitud, pero no pude guardarla en Firebase.")
                else:
                    enviar_mensaje(numero_remitente, "❌ Error de análisis de IA.")
            elif numero_remitente:
                enviar_mensaje(numero_remitente, "❌ No pude procesar tu solicitud. Envíame texto o audio claro.")
        except Exception as e:
            print(f"❌ Error en webhook: {e}")
            if numero_remitente:
                enviar_mensaje(numero_remitente, "❌ Ocurrió un error al completar tu solicitud. Intenta de nuevo.")
        return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)