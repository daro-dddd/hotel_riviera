# servidor.py
# Servidor principal de Python con Flask para la hotelera "Hotel Riviera".
# Comentado en español para facilitar el aprendizaje y la comprensión escolar.

import os
import threading
import smtplib
import re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, send_from_directory, request, jsonify
from mysql.connector import pooling
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Cargar las variables del archivo .env
load_dotenv()

app = Flask(__name__, static_folder='public', static_url_path='')

# =====================================================================
# CONFIGURACIÓN DE CONEXIÓN A MYSQL (POOL DE CONEXIONES)
# =====================================================================
db_config = {
    "database": os.getenv("DB_NAME", os.getenv("MYSQLDATABASE", "HotelDB")),
    "user":     os.getenv("DB_USER", os.getenv("MYSQLUSER", "root")),
    "password": os.getenv("DB_PASSWORD", os.getenv("MYSQLPASSWORD", "root")),
    "host":     os.getenv("DB_HOST", os.getenv("MYSQLHOST", "localhost")),
    "port":     int(os.getenv("DB_PORT", os.getenv("MYSQLPORT", 3306))),
    "charset":  "utf8mb4"
}

try:
    # Creamos un pool de conexiones para hacer consultas de forma eficiente
    conexion_pool = pooling.MySQLConnectionPool(
        pool_name="pool_hotel",
        pool_size=5,
        **db_config
    )
    print("¡Conexión exitosa a la base de datos MySQL en Python!")
except Exception as e:
    print("--- ERROR AL CONECTARSE A MYSQL ---")
    print(f"Detalle del error: {e}")
    print("Asegúrate de que MySQL esté prendido y que los datos en tu archivo .env sean correctos.")
    print("------------------------------------")
    conexion_pool = None

# Helper para ejecutar consultas MySQL de forma segura y automática
def ejecutar_consulta(query, params=(), commit=False, fetchall=True, fetchone=False):
    if not conexion_pool:
        raise Exception("El pool de conexiones a la base de datos no está inicializado.")
    
    conexion = conexion_pool.get_connection()
    cursor = conexion.cursor(dictionary=True) # Regresa las filas como diccionarios {'campo': valor}
    try:
        cursor.execute(query, params)
        if commit:
            conexion.commit()
            return cursor.lastrowid
        else:
            if fetchone:
                return cursor.fetchone()
            return cursor.fetchall() if fetchall else None
    except Exception as err:
        conexion.rollback()
        raise err
    finally:
        cursor.close()
        conexion.close()

def inicializar_columnas_adicionales():
    if not conexion_pool:
        print("[DB Setup] No se pudo inicializar columnas: no hay pool de conexiones.")
        return
    try:
        # Verificar si la columna Eliminado existe en Testimonios
        col_eliminado = ejecutar_consulta("SHOW COLUMNS FROM Testimonios LIKE 'Eliminado'")
        if not col_eliminado:
            ejecutar_consulta("ALTER TABLE Testimonios ADD COLUMN Eliminado BOOLEAN DEFAULT FALSE", commit=True)
            print("[DB Setup] Columna 'Eliminado' agregada a la tabla Testimonios.")
        else:
            print("[DB Setup] Columna 'Eliminado' ya existe en la tabla Testimonios.")
            
        # Verificar si la columna Precio_Noche_Reservado existe en Reservas
        col_precio = ejecutar_consulta("SHOW COLUMNS FROM Reservas LIKE 'Precio_Noche_Reservado'")
        if not col_precio:
            ejecutar_consulta("ALTER TABLE Reservas ADD COLUMN Precio_Noche_Reservado DECIMAL(10,2) NULL", commit=True)
            print("[DB Setup] Columna 'Precio_Noche_Reservado' agregada a la tabla Reservas.")
        else:
            print("[DB Setup] Columna 'Precio_Noche_Reservado' ya existe en la tabla Reservas.")
            
        # Verificar si la columna Estado en Habitaciones ya acepta 'Reservada'
        col_estado = ejecutar_consulta("SHOW COLUMNS FROM Habitaciones LIKE 'Estado'")
        if col_estado:
            tipo_col = col_estado[0]['Type']
            if 'Reservada' not in tipo_col:
                ejecutar_consulta("ALTER TABLE Habitaciones MODIFY COLUMN Estado ENUM('Disponible', 'Ocupada', 'Mantenimiento', 'Reservada') DEFAULT 'Disponible'", commit=True)
                print("[DB Setup] Columna 'Estado' de Habitaciones modificada para incluir 'Reservada'.")
            else:
                print("[DB Setup] Columna 'Estado' de Habitaciones ya incluye 'Reservada'.")
    except Exception as e:
        print(f"[DB Setup Error] Error al configurar columnas adicionales: {e}")

# Ejecutar la inicialización dinámica de columnas
inicializar_columnas_adicionales()

# =====================================================================
# ENVÍO DE TICKETS DE RESERVA POR CORREO (SMTP HILADO)
# =====================================================================

def generar_html_correo_ticket(datos_reserva, servicios):
    # Calculamos datos para el ticket de correo
    llegada = datos_reserva['Fecha_Llegada']
    salida = datos_reserva['Fecha_Salida']
    diferencia = salida - llegada
    noches = max(diferencia.days, 1)
    
    precio_noche = float(datos_reserva['Precio_Noche'])
    costo_hospedaje = precio_noche * noches
    
    costo_servicios = 0.0
    servicios_html = ""
    for s in servicios:
        sub = float(s['Precio']) * int(s['Cantidad'])
        costo_servicios += sub
        precio_mxn = float(s['Precio']) * 20.00
        precio_texto = "Incluido" if float(s['Precio']) == 0 else f"${precio_mxn:,.2f} MXN"
        servicios_html += f"<tr><td>{s['Nombre_Servicio']}</td><td style='text-align:right;'>{precio_texto}</td></tr>"
    
    if not servicios:
        servicios_html = "<tr><td colspan='2' style='color:#777; font-style:italic;'>Ninguno</td></tr>"
        
    costo_hospedaje_mxn = costo_hospedaje * 20.00
    costo_servicios_mxn = costo_servicios * 20.00
    total_mxn = costo_hospedaje_mxn + costo_servicios_mxn
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border: 1px solid #e0e0e0;">
            <div style="background-color: #003064; color: #ffffff; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">Confirmación de Reserva</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.85;">¡Gracias por elegir Hotel Riviera!</p>
            </div>
            <div style="padding: 30px;">
                <h2 style="color: #003064; border-bottom: 2px solid #eef5fc; padding-bottom: 8px; margin-top: 0;">Folio de Reserva: #{datos_reserva['ID_Reserva']}</h2>
                
                <table style="width: 100%; font-size: 14px; margin-bottom: 20px; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold; width: 150px;">Huésped:</td>
                        <td style="padding: 6px 0;">{datos_reserva['Nombre']} {datos_reserva['Apellido']}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold;">Correo:</td>
                        <td style="padding: 6px 0;">{datos_reserva['Email']}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold;">Teléfono:</td>
                        <td style="padding: 6px 0;">{datos_reserva['Telefono'] or 'No especificado'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold;">Habitación:</td>
                        <td style="padding: 6px 0;">{datos_reserva['Nombre_Tipo']} (Habitación #{datos_reserva['Numero_Habitacion']})</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold;">Entrada (Check-in):</td>
                        <td style="padding: 6px 0;">{llegada.strftime('%Y-%m-%d')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold;">Salida (Check-out):</td>
                        <td style="padding: 6px 0;">{salida.strftime('%Y-%m-%d')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold;">Huéspedes:</td>
                        <td style="padding: 6px 0;">{datos_reserva['Numero_Adultos']} Adultos, {datos_reserva['Numero_Ninos']} Niños</td>
                    </tr>
                </table>

                <h3 style="color: #003064; margin-bottom: 10px; font-size: 16px;">Servicios Adicionales contratados:</h3>
                <table style="width: 100%; font-size: 13px; margin-bottom: 30px; border-bottom: 1px solid #eef5fc;">
                    {servicios_html}
                </table>

                <div style="background-color: #fafafa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 20px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">
                        <span>Hospedaje ({noches} noches):</span>
                        <strong style="float: right;">${costo_hospedaje_mxn:,.2f} MXN</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; clear: both;">
                        <span>Servicios Adicionales:</span>
                        <strong style="float: right;">${costo_servicios_mxn:,.2f} MXN</strong>
                    </div>
                    <div style="border-top: 1px dashed #ccc; padding-top: 12px; margin-top: 12px; font-size: 18px; font-weight: bold; color: #003064; clear: both;">
                        <span>Total Pagado:</span>
                        <span style="float: right;">${total_mxn:,.2f} MXN</span>
                    </div>
                </div>
            </div>
            <div style="background-color: #eef5fc; padding: 20px; text-align: center; font-size: 12px; color: #555;">
                <p style="margin: 0;">Este es un boleto digital que confirma tu compra y reservación. Presenta este correo o tu ticket impreso al llegar al lobby.</p>
                <p style="margin: 5px 0 0 0;">&copy; 2026 Hotel Riviera. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def enviar_correo_ticket_worker(reserva_id, email_destinatario):
    # Buscamos la información detallada de la reserva
    query_reserva = """
        SELECT r.ID_Reserva, r.Fecha_Llegada, r.Fecha_Salida, r.Numero_Adultos, r.Numero_Ninos,
               h.Numero_Habitacion, th.Nombre_Tipo,
               COALESCE(r.Precio_Noche_Reservado, th.Precio_Noche) as Precio_Noche,
               hu.Nombre, hu.Apellido, hu.Telefono, hu.Email
        FROM Reservas r
        JOIN Habitaciones h ON r.ID_Habitacion = h.ID_Habitacion
        JOIN Tipos_Habitacion th ON h.ID_Tipo_Habitacion = th.ID_Tipo_Habitacion
        JOIN Huespedes hu ON r.ID_Huesped = hu.ID_Huesped
        WHERE r.ID_Reserva = %s
    """
    try:
        filas = ejecutar_consulta(query_reserva, (reserva_id,), fetchone=True)
        if not filas:
            print(f"[Error Email] No se encontró la reserva con ID {reserva_id}")
            return
            
        # Buscamos los servicios
        query_servicios = """
            SELECT s.Nombre_Servicio, s.Precio, rs.Cantidad
            FROM Reservas_Servicios rs
            JOIN Servicios s ON rs.ID_Servicio = s.ID_Servicio
            WHERE rs.ID_Reserva = %s
        """
        servicios = ejecutar_consulta(query_servicios, (reserva_id,))
        
        # Leer variables de configuración
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        
        if not smtp_user or "tu_correo@gmail.com" in smtp_user:
            print(f"[Simulación de Correo] Envío para #{reserva_id} simulado exitosamente a {email_destinatario}. (Configura SMTP en .env para envío real)")
            return
            
        # Configurar mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Tu ticket de reservación en Hotel Riviera - Folio #{reserva_id}"
        msg['From'] = smtp_user
        msg['To'] = email_destinatario
        
        html_content = generar_html_correo_ticket(filas, servicios)
        part_html = MIMEText(html_content, 'html')
        msg.attach(part_html)
        
        # Conexión al servidor SMTP
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email_destinatario, msg.as_string())
        server.quit()
        
        print(f"[Email Enviado] Ticket de reserva #{reserva_id} enviado a {email_destinatario} con éxito.")
    except Exception as e:
        print(f"[Error Email] Ocurrió una falla al enviar el correo SMTP: {e}")

# Ejecuta el envío de correo en segundo plano para no demorar la respuesta de la API al frontend
def enviar_correo_ticket_async(reserva_id, email_destinatario):
    t = threading.Thread(target=enviar_correo_ticket_worker, args=(reserva_id, email_destinatario))
    t.start()


def generar_html_correo_cancelacion(detalles):
    llegada = detalles['Fecha_Llegada']
    salida = detalles['Fecha_Salida']
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border: 1px solid #e0e0e0;">
            <div style="background-color: #d32f2f; color: #ffffff; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">Cancelación de Reserva</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.85;">Tu reservación ha sido cancelada exitosamente</p>
            </div>
            <div style="padding: 30px;">
                <h2 style="color: #d32f2f; border-bottom: 2px solid #fdebee; padding-bottom: 8px; margin-top: 0;">Folio Cancelado: #{detalles['ID_Reserva']}</h2>
                
                <p>Hola <strong>{detalles['Nombre']} {detalles['Apellido']}</strong>,</p>
                <p>Te confirmamos que de acuerdo a tu solicitud, la reservación con folio <strong>#{detalles['ID_Reserva']}</strong> ha sido cancelada en nuestro sistema.</p>
                
                <table style="width: 100%; font-size: 14px; margin-top: 20px; margin-bottom: 20px; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold; width: 150px;">Habitación:</td>
                        <td style="padding: 6px 0;">{detalles['Nombre_Tipo']} (Habitación #{detalles['Numero_Habitacion']})</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold;">Fecha de Entrada:</td>
                        <td style="padding: 6px 0;">{llegada.strftime('%Y-%m-%d') if hasattr(llegada, 'strftime') else llegada}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold;">Fecha de Salida:</td>
                        <td style="padding: 6px 0;">{salida.strftime('%Y-%m-%d') if hasattr(salida, 'strftime') else salida}</td>
                    </tr>
                </table>
                
                <p style="color: #555; font-size: 13px; line-height: 1.5;">El reembolso, si aplica, se procesará en los siguientes 5 a 10 días hábiles en la misma tarjeta con la que realizaste el pago.</p>
            </div>
            <div style="background-color: #fdebee; padding: 20px; text-align: center; font-size: 12px; color: #555;">
                <p style="margin: 0;">Lamentamos que hayas tenido que cancelar. ¡Esperamos hospedarte pronto en Hotel Riviera!</p>
                <p style="margin: 5px 0 0 0;">&copy; 2026 Hotel Riviera. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def enviar_correo_cancelacion_worker(detalles):
    try:
        email_destinatario = detalles['Email']
        reserva_id = detalles['ID_Reserva']
        
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        
        if not smtp_user or "tu_correo@gmail.com" in smtp_user:
            print(f"[Simulación de Correo] Envío de cancelación para #{reserva_id} simulado a {email_destinatario}.")
            return
            
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Cancelación de Reservación en Hotel Riviera - Folio #{reserva_id}"
        msg['From'] = smtp_user
        msg['To'] = email_destinatario
        
        html_content = generar_html_correo_cancelacion(detalles)
        part_html = MIMEText(html_content, 'html')
        msg.attach(part_html)
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email_destinatario, msg.as_string())
        server.quit()
        
        print(f"[Email Enviado] Confirmación de cancelación #{reserva_id} enviada a {email_destinatario}.")
    except Exception as e:
        print(f"[Error Email] Ocurrió una falla al enviar el correo de cancelación: {e}")

def enviar_correo_cancelacion_async(detalles):
    t = threading.Thread(target=enviar_correo_cancelacion_worker, args=(detalles,))
    t.start()

# --- FUNCIONES DE ENVÍO DE CORREO DE BOLETÍN ---
def generar_html_correo_suscripcion(email_destinatario):
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
            body {{
                margin: 0;
                padding: 0;
                background-color: #eef5fc;
                font-family: 'Outfit', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                color: #333333;
            }}
            .contenedor {{
                max-width: 600px;
                margin: 30px auto;
                background-color: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 8px 30px rgba(0, 48, 100, 0.08);
            }}
            .cabecera {{
                background-color: #003064;
                padding: 40px 20px;
                text-align: center;
                color: #ffffff;
            }}
            .cabecera h1 {{
                margin: 0;
                font-size: 26px;
                font-weight: 700;
                letter-spacing: -0.5px;
            }}
            .cabecera p {{
                margin: 5px 0 0 0;
                font-size: 14px;
                opacity: 0.85;
            }}
            .banner-img {{
                width: 100%;
                height: 240px;
                object-fit: cover;
                display: block;
            }}
            .contenido {{
                padding: 40px 35px;
            }}
            .contenido h2 {{
                margin-top: 0;
                font-size: 22px;
                color: #001e3d;
                font-weight: 600;
            }}
            .contenido p {{
                font-size: 15px;
                line-height: 1.6;
                color: #555555;
            }}
            .bono-tarjeta {{
                background-color: #eef5fc;
                border: 1px dashed #003064;
                border-radius: 8px;
                padding: 25px;
                text-align: center;
                margin: 30px 0;
            }}
            .bono-titulo {{
                font-size: 13px;
                font-weight: 700;
                color: #003064;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 5px;
            }}
            .bono-codigo {{
                font-size: 28px;
                font-weight: 700;
                color: #d4a373;
                margin: 10px 0;
                letter-spacing: 2px;
            }}
            .bono-detalle {{
                font-size: 12px;
                color: #777777;
                margin: 0;
            }}
            .beneficios {{
                margin: 30px 0 10px 0;
                padding-left: 20px;
            }}
            .beneficios li {{
                font-size: 14px;
                color: #555555;
                margin-bottom: 12px;
                line-height: 1.5;
            }}
            .boton-link {{
                display: block;
                text-align: center;
                background-color: #003064;
                color: #ffffff !important;
                text-decoration: none;
                padding: 15px 30px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 16px;
                margin-top: 30px;
                box-shadow: 0 5px 15px rgba(0, 48, 100, 0.2);
            }}
            .pie {{
                background-color: #001e3d;
                padding: 25px;
                text-align: center;
                font-size: 12px;
                color: #bccbdc;
            }}
            .pie p {{
                margin: 0 0 5px 0;
            }}
            .pie a {{
                color: #d4a373;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="contenedor">
            <div class="cabecera">
                <h1>Hotel Riviera</h1>
                <p>Tu Destino Ideal de Descanso</p>
            </div>
            
            <img class="banner-img" src="https://images.unsplash.com/photo-1540541338287-41700207dee6?auto=format&fit=crop&w=600&q=80" alt="Alberca de Lujo del Hotel Riviera">
            
            <div class="contenido">
                <h2>¡Gracias por suscribirte a nuestro boletín!</h2>
                <p>Nos complace darte la bienvenida a nuestra comunidad exclusiva. A partir de ahora, serás el primero en enterarte de nuestras ofertas especiales, lanzamientos de temporada, novedades del resort y beneficios exclusivos en hospedaje y servicios.</p>
                
                <div class="bono-tarjeta">
                    <p class="bono-titulo">Tu Regalo de Bienvenida</p>
                    <p class="bono-codigo">RIVIERAWELCOME</p>
                    <p class="bono-detalle">Úsalo al reservar en nuestro lobby para recibir un 10% de descuento en tu primera estadía de hospedaje.</p>
                </div>
                
                <p>Como suscriptor exclusivo del Hotel Riviera, disfrutarás de:</p>
                <ul class="beneficios">
                    <li><strong>Ofertas de Temporada Anticipadas:</strong> Reserva antes que nadie y obtén las mejores tarifas en suites y villas de playa.</li>
                    <li><strong>Bonos y Descuentos en Servicios Adicionales:</strong> Promociones exclusivas en nuestro Spa & Wellness Center y Restaurante Gourmet.</li>
                    <li><strong>Guías y Tips de Viaje:</strong> Recomendaciones locales para hacer de tus vacaciones una experiencia inolvidable.</li>
                </ul>
                
                <a href="https://hotel-riviera-3v5f.onrender.com/" class="boton-link">Explorar Habitaciones y Reservar</a>
            </div>
            
            <div class="pie">
                <p>&copy; 2026 Hotel Riviera. Todos los derechos reservados.</p>
                <p>Recibes este correo porque te suscribiste a nuestro boletín en <a href="https://hotel-riviera-3v5f.onrender.com/">hotel-riviera-3v5f.onrender.com</a>.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def enviar_correo_suscripcion_worker(email_destinatario):
    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        
        if not smtp_user or "tu_correo@gmail.com" in smtp_user:
            print(f"[Simulación de Correo] Envío de confirmación de boletín a {email_destinatario} simulado con éxito.")
            return
            
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "¡Bienvenido al boletín exclusivo de Hotel Riviera!"
        msg['From'] = smtp_user
        msg['To'] = email_destinatario
        
        html_content = generar_html_correo_suscripcion(email_destinatario)
        part_html = MIMEText(html_content, 'html')
        msg.attach(part_html)
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email_destinatario, msg.as_string())
        server.quit()
        
        print(f"[Email Enviado] Confirmación de suscripción al boletín enviada a {email_destinatario} con éxito.")
    except Exception as e:
        print(f"[Error Email] Ocurrió una falla al enviar el correo de suscripción: {e}")

def enviar_correo_suscripcion_async(email_destinatario):
    t = threading.Thread(target=enviar_correo_suscripcion_worker, args=(email_destinatario,))
    t.start()


# =====================================================================
# RUTAS DE ARCHIVOS ESTÁTICOS
# =====================================================================

@app.route('/')
def principal():
    # Sirve el index.html desde la carpeta public
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def servir_archivos(path):
    # Sirve estilos, imágenes o scripts desde la carpeta public
    return send_from_directory(app.static_folder, path)


# =====================================================================
# RUTAS API (Estructuradas en español de forma simple)
# =====================================================================

# 1. Ruta para el Registro de Huéspedes
@app.route('/api/registrar', methods=['POST'])
def registrar():
    datos = request.get_json()
    nombre = datos.get('nombre')
    apellido = datos.get('apellido')
    email = datos.get('email', '').strip().lower() if datos.get('email') else None
    contrasena = datos.get('contrasena')
    telefono = datos.get('telefono')

    if not nombre or not apellido or not email or not contrasena:
        return jsonify({'error': 'Llene todos los campos obligatorios.'}), 400

    if telefono:
        if not re.match(r'^\+[0-9]{12}$', telefono):
            return jsonify({'error': 'El número de teléfono debe tener el formato "+" seguido de 12 dígitos numéricos (ej. +521234567890).'}), 400

    try:
        # Validar si ya existe
        existe = ejecutar_consulta('SELECT ID_Huesped FROM Huespedes WHERE Email = %s', (email,))
        if existe:
            return jsonify({'error': 'Este correo electrónico ya está registrado.'}), 400

        # Cifrar contraseña usando Werkzeug hash
        hash_contrasena = generate_password_hash(contrasena)

        # Insertar
        id_creado = ejecutar_consulta(
            'INSERT INTO Huespedes (Nombre, Apellido, Email, Contrasena, Telefono) VALUES (%s, %s, %s, %s, %s)',
            (nombre, apellido, email, hash_contrasena, telefono or None),
            commit=True
        )

        return jsonify({
            'mensaje': '¡Registro exitoso!',
            'usuario': {
                'id': id_creado,
                'nombre': nombre,
                'apellido': apellido,
                'email': email,
                'telefono': telefono
            }
        }), 201
    except Exception as err:
        print(f"Error al registrar: {err}")
        return jsonify({'error': 'Falla del servidor al registrar.'}), 500

# 2. Iniciar Sesión (Login)
@app.route('/api/iniciar-sesion', methods=['POST'])
def iniciar_sesion():
    datos = request.get_json()
    email = datos.get('email', '').strip().lower() if datos.get('email') else None
    contrasena = datos.get('contrasena')

    if not email or not contrasena:
        return jsonify({'error': 'Ingresa tu correo y contraseña.'}), 400

    try:
        # Primero verificamos si el correo existe y obtenemos los datos
        usuario = ejecutar_consulta(
            'SELECT ID_Huesped, Nombre, Apellido, Email, Contrasena, Telefono, Es_Administrador FROM Huespedes WHERE Email = %s',
            (email,),
            fetchone=True
        )
        if not usuario:
            return jsonify({'error': 'Este correo electrónico no está registrado. Por favor, cree una cuenta nueva.'}), 404

        # Verificar contraseña
        contrasena_db = usuario['Contrasena']
        es_valida = False
        
        # Si parece un hash seguro
        if contrasena_db.startswith(('pbkdf2:', 'scrypt:', 'bcrypt:', 'sha256:')) or '$' in contrasena_db:
            es_valida = check_password_hash(contrasena_db, contrasena)
        else:
            # Fallback para contraseñas antiguas guardadas en texto plano
            es_valida = (contrasena_db == contrasena)
            if es_valida:
                # Actualizar/Migrar a hash cifrado
                try:
                    hash_contrasena = generate_password_hash(contrasena)
                    ejecutar_consulta(
                        'UPDATE Huespedes SET Contrasena = %s WHERE ID_Huesped = %s',
                        (hash_contrasena, usuario['ID_Huesped']),
                        commit=True
                    )
                    print(f"[Seguridad] Contraseña de usuario ID {usuario['ID_Huesped']} migrada exitosamente al iniciar sesión.")
                except Exception as ex_mig:
                    print(f"[Seguridad Error] Falló la migración automática de contraseña: {ex_mig}")

        if not es_valida:
            return jsonify({'error': 'La contraseña es incorrecta.'}), 401

        return jsonify({
            'mensaje': '¡Inicio de sesión correcto!',
            'usuario': {
                'id': usuario['ID_Huesped'],
                'nombre': usuario['Nombre'],
                'apellido': usuario['Apellido'],
                'email': usuario['Email'],
                'telefono': usuario['Telefono'],
                'es_admin': bool(usuario['Es_Administrador'])
            }
        })
    except Exception as err:
        print(f"Error en login: {err}")
        return jsonify({'error': 'Error del servidor al iniciar sesión.'}), 500

# 2.5. Obtener Perfil del Huésped
@app.route('/api/perfil', methods=['GET'])
def obtener_perfil():
    huesped_id = request.args.get('id')
    if not huesped_id:
        return jsonify({'error': 'Falta el ID del huésped.'}), 400
    try:
        usuario = ejecutar_consulta(
            'SELECT ID_Huesped, Nombre, Apellido, Email, Telefono, Es_Administrador FROM Huespedes WHERE ID_Huesped = %s',
            (huesped_id,),
            fetchone=True
        )
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado.'}), 404
        return jsonify({
            'usuario': {
                'id': usuario['ID_Huesped'],
                'nombre': usuario['Nombre'],
                'apellido': usuario['Apellido'],
                'email': usuario['Email'],
                'telefono': usuario['Telefono'],
                'es_admin': bool(usuario['Es_Administrador'])
            }
        })
    except Exception as err:
        print(f"Error al obtener perfil: {err}")
        return jsonify({'error': 'Error de base de datos al obtener el perfil.'}), 500

# 3. Consultar Habitaciones Disponibles por rango de fechas
@app.route('/api/habitaciones-disponibles', methods=['GET'])
def habitaciones_disponibles():
    llegada = request.args.get('llegada')
    salida = request.args.get('salida')

    try:
        # Si no mandan fechas, regresamos todos los tipos de habitaciones con su conteo de físicas activas (Únicamente Disponibles)
        if not llegada or not salida:
            query = """
                SELECT th.ID_Tipo_Habitacion, th.Nombre_Tipo, th.Descripcion, th.Capacidad_Maxima, th.Precio_Noche,
                       COALESCE(SUM(CASE WHEN h.Estado = 'Disponible' THEN 1 ELSE 0 END), 0) as Habitaciones_Disponibles
                FROM Tipos_Habitacion th
                LEFT JOIN Habitaciones h ON th.ID_Tipo_Habitacion = h.ID_Tipo_Habitacion
                GROUP BY th.ID_Tipo_Habitacion
            """
            tipos = ejecutar_consulta(query)
            # Convertir decimales para JSON
            for t in tipos:
                t['Precio_Noche'] = float(t['Precio_Noche'])
            return jsonify(tipos)

        # Si sí mandan fechas, buscamos habitaciones físicas libres (con estado Disponible o Reservada pero sin reservas traslapadas)
        query_disponible = """
            SELECT th.ID_Tipo_Habitacion, th.Nombre_Tipo, th.Descripcion, th.Capacidad_Maxima, th.Precio_Noche,
                   COALESCE(COUNT(h.ID_Habitacion), 0) as Habitaciones_Disponibles
            FROM Tipos_Habitacion th
            LEFT JOIN Habitaciones h ON th.ID_Tipo_Habitacion = h.ID_Tipo_Habitacion
                AND h.Estado IN ('Disponible', 'Reservada')
                AND h.ID_Habitacion NOT IN (
                    SELECT ID_Habitacion 
                    FROM Reservas 
                    WHERE Estado_Reserva IN ('Pendiente', 'Confirmada')
                    AND NOT (Fecha_Salida <= %s OR Fecha_Llegada >= %s)
                )
            GROUP BY th.ID_Tipo_Habitacion;
        """
        resultado = ejecutar_consulta(query_disponible, (llegada, salida))
        for r in resultado:
            r['Precio_Noche'] = float(r['Precio_Noche'])
        return jsonify(resultado)
    except Exception as err:
        print(f"Error al buscar disponibles: {err}")
        return jsonify({'error': 'Error al buscar disponibilidad.'}), 500

# 4. Obtener Servicios del catálogo
@app.route('/api/servicios', methods=['GET'])
def obtener_servicios():
    try:
        servicios = ejecutar_consulta('SELECT * FROM Servicios WHERE Disponible = TRUE')
        return jsonify(servicios)
    except Exception as err:
        print(f"Error al obtener servicios: {err}")
        return jsonify({'error': 'Error al obtener servicios.'}), 500

# 5. Obtener Testimonios Aprobados
@app.route('/api/testimonios', methods=['GET'])
def obtener_testimonios():
    try:
        query = """
            SELECT t.ID_Testimonio, t.Comentario, t.Calificacion_Estrellas, t.Fecha_Publicacion,
                   h.Nombre, h.Apellido, h.URL_Foto_Perfil
            FROM Testimonios t
            JOIN Huespedes h ON t.ID_Huesped = h.ID_Huesped
            WHERE t.Aprobado = TRUE AND (t.Eliminado IS NULL OR t.Eliminado = FALSE)
            ORDER BY t.Fecha_Publicacion DESC
        """
        testimonios = ejecutar_consulta(query)
        # Convertir fechas a string para serializar con JSON
        for t in testimonios:
            if isinstance(t['Fecha_Publicacion'], datetime) or hasattr(t['Fecha_Publicacion'], 'strftime'):
                t['Fecha_Publicacion'] = t['Fecha_Publicacion'].strftime('%Y-%m-%d')
        return jsonify(testimonios)
    except Exception as err:
        print(f"Error al obtener testimonios: {err}")
        return jsonify({'error': 'Error al obtener testimonios.'}), 500

# 6. Escribir Testimonio
@app.route('/api/testimonios', methods=['POST'])
def escribir_testimonio():
    datos = request.get_json()
    id_huesped = datos.get('id_huesped')
    comentario = datos.get('comentario')
    calificacion = datos.get('calificacion')

    if not id_huesped or not comentario or not calificacion:
        return jsonify({'error': 'Faltan datos requeridos.'}), 400

    try:
        ejecutar_consulta(
            'INSERT INTO Testimonios (ID_Huesped, Comentario, Calificacion_Estrellas, Aprobado) VALUES (%s, %s, %s, TRUE)',
            (id_huesped, comentario, calificacion),
            commit=True
        )
        return jsonify({'mensaje': '¡Testimonio publicado con éxito!'}), 201
    except Exception as err:
        print(f"Error al guardar testimonio: {err}")
        return jsonify({'error': 'Error al publicar testimonio.'}), 500

# 7. Crear una Reservación y pagar con Tarjeta (Flujo Completo)
@app.route('/api/reservar', methods=['POST'])
def reservar():
    datos = request.get_json()
    id_huesped = datos.get('id_huesped')
    id_tipo_habitacion = datos.get('id_tipo_habitacion')
    fecha_llegada = datos.get('fecha_llegada')
    fecha_salida = datos.get('fecha_salida')
    adultos = datos.get('adultos')
    ninos = datos.get('ninos', 0)
    servicios = datos.get('servicios', [])
    
    # Datos del pago (Tarjeta)
    tarjeta_nombre = datos.get('tarjeta_nombre')
    tarjeta_numero = datos.get('tarjeta_numero')
    
    if not id_huesped or not id_tipo_habitacion or not fecha_llegada or not fecha_salida or not adultos:
        return jsonify({'error': 'Faltan datos de reservación.'}), 400
        
    if not tarjeta_nombre or not tarjeta_numero:
        return jsonify({'error': 'Es obligatorio proporcionar los detalles de pago para realizar la reserva.'}), 400

    try:
        # Validar fechas
        formato = "%Y-%m-%d"
        flleg = datetime.strptime(fecha_llegada, formato)
        fsal = datetime.strptime(fecha_salida, formato)
        if fsal <= flleg:
            return jsonify({'error': 'La fecha de salida debe ser después de la fecha de llegada.'}), 400

        # Buscar habitación física disponible (que esté activa y sin reservas traslapadas)
        query_libre = """
            SELECT ID_Habitacion 
            FROM Habitaciones 
            WHERE ID_Tipo_Habitacion = %s 
            AND Estado IN ('Disponible', 'Reservada')
            AND ID_Habitacion NOT IN (
                SELECT ID_Habitacion 
                FROM Reservas 
                WHERE Estado_Reserva IN ('Pendiente', 'Confirmada')
                AND NOT (Fecha_Salida <= %s OR Fecha_Llegada >= %s)
            )
            LIMIT 1
        """
        habitaciones = ejecutar_consulta(query_libre, (id_tipo_habitacion, fecha_llegada, fecha_salida))
        if not habitaciones:
            return jsonify({'error': 'Lo sentimos, ya no hay habitaciones físicas disponibles de este tipo para las fechas seleccionadas.'}), 400

        id_habitacion = habitaciones[0]['ID_Habitacion']

        # Obtener el precio actual por noche de la habitación para congelarlo en el registro
        tipo_hab = ejecutar_consulta(
            'SELECT Precio_Noche FROM Tipos_Habitacion WHERE ID_Tipo_Habitacion = %s',
            (id_tipo_habitacion,),
            fetchone=True
        )
        if not tipo_hab:
            return jsonify({'error': 'El tipo de habitación no es válido.'}), 400
        precio_noche_actual = float(tipo_hab['Precio_Noche'])

        # Crear reserva en la base de datos congelando el precio actual por noche
        id_reserva = ejecutar_consulta(
            """INSERT INTO Reservas (ID_Huesped, ID_Habitacion, Fecha_Llegada, Fecha_Salida, Numero_Adultos, Numero_Ninos, Estado_Reserva, Precio_Noche_Reservado) 
               VALUES (%s, %s, %s, %s, %s, %s, 'Confirmada', %s)""",
            (id_huesped, id_habitacion, fecha_llegada, fecha_salida, adultos, ninos, precio_noche_actual),
            commit=True
        )

        # Actualizar el estado de la habitación física a Reservada
        ejecutar_consulta(
            'UPDATE Habitaciones SET Estado = "Reservada" WHERE ID_Habitacion = %s',
            (id_habitacion,),
            commit=True
        )

        # Registrar servicios asociados
        if servicios and isinstance(servicios, list):
            for serv in servicios:
                ejecutar_consulta(
                    'INSERT INTO Reservas_Servicios (ID_Reserva, ID_Servicio, Cantidad) VALUES (%s, %s, %s)',
                    (id_reserva, serv['id_servicio'], serv.get('cantidad', 1)),
                    commit=True
                )

        # Buscar el email del huésped para mandarle el correo
        datos_huesped = ejecutar_consulta(
            'SELECT Email FROM Huespedes WHERE ID_Huesped = %s', (id_huesped,), fetchone=True
        )
        if datos_huesped:
            # Mandamos el correo en segundo plano
            enviar_correo_ticket_async(id_reserva, datos_huesped['Email'])

        return jsonify({
            'mensaje': '¡Reserva y Pago procesados con éxito!',
            'id_reserva': id_reserva,
            'id_habitacion': id_habitacion
        }), 201

    except Exception as err:
        print(f"Error al reservar: {err}")
        return jsonify({'error': 'Error de base de datos al realizar reserva.'}), 500

# 8. Obtener Reservas del huésped logueado
@app.route('/api/mis-reservas', methods=['GET'])
def mis_reservas():
    id_huesped = request.args.get('id_huesped')
    if not id_huesped:
        return jsonify({'error': 'Se requiere el ID del huésped.'}), 400

    try:
        query = """
            SELECT r.ID_Reserva, r.Fecha_Llegada, r.Fecha_Salida, r.Numero_Adultos, r.Numero_Ninos, r.Estado_Reserva, r.Fecha_Creacion,
                   h.Numero_Habitacion, th.Nombre_Tipo, 
                   COALESCE(r.Precio_Noche_Reservado, th.Precio_Noche) as Precio_Noche,
                   (DATEDIFF(r.Fecha_Salida, r.Fecha_Llegada) * COALESCE(r.Precio_Noche_Reservado, th.Precio_Noche)) as Costo_Hospedaje
            FROM Reservas r
            JOIN Habitaciones h ON r.ID_Habitacion = h.ID_Habitacion
            JOIN Tipos_Habitacion th ON h.ID_Tipo_Habitacion = th.ID_Tipo_Habitacion
            WHERE r.ID_Huesped = %s
            ORDER BY r.Fecha_Creacion DESC
        """
        reservas = ejecutar_consulta(query, (id_huesped,))
        
        resultado_final = []
        for r in reservas:
            # Formatear fechas para JSON
            if hasattr(r['Fecha_Llegada'], 'strftime'):
                r['Fecha_Llegada'] = r['Fecha_Llegada'].strftime('%Y-%m-%d')
            if hasattr(r['Fecha_Salida'], 'strftime'):
                r['Fecha_Salida'] = r['Fecha_Salida'].strftime('%Y-%m-%d')
            if hasattr(r['Fecha_Creacion'], 'strftime'):
                r['Fecha_Creacion'] = r['Fecha_Creacion'].strftime('%Y-%m-%d %H:%M:%S')

            # Buscar servicios contratados
            q_servs = """
                SELECT s.Nombre_Servicio, s.Precio, rs.Cantidad, (s.Precio * rs.Cantidad) as Costo_Servicio
                FROM Reservas_Servicios rs
                JOIN Servicios s ON rs.ID_Servicio = s.ID_Servicio
                WHERE rs.ID_Reserva = %s
            """
            servs = ejecutar_consulta(q_servs, (r['ID_Reserva'],))
            
            costo_servs_total = 0.0
            for s in servs:
                costo_servs_total += float(s['Costo_Servicio'] or 0.0)
                # Convertir decimales para JSON
                s['Precio'] = float(s['Precio'])
                s['Costo_Servicio'] = float(s['Costo_Servicio'])
                
            costo_hospedaje = float(r['Costo_Hospedaje'])
            costo_total = costo_hospedaje + costo_servs_total
            
            r['Precio_Noche'] = float(r['Precio_Noche'])
            r['Costo_Hospedaje'] = costo_hospedaje
            r['Costo_Total'] = costo_total
            r['ServiciosAdicionales'] = servs
            resultado_final.append(r)
            
        return jsonify(resultado_final)
    except Exception as err:
        print(f"Error al obtener reservas: {err}")
        return jsonify({'error': 'Error de base de datos al obtener historial.'}), 500

# 9. Cancelar una Reserva
@app.route('/api/cancelar-reserva', methods=['POST'])
def cancelar_reserva():
    datos = request.get_json()
    id_reserva = datos.get('id_reserva')
    id_huesped = datos.get('id_huesped')

    if not id_reserva or not id_huesped:
        return jsonify({'error': 'Faltan datos de cancelación.'}), 400

    try:
        # Obtener información del huésped y de la reserva para el correo antes de cancelar
        query_res = """
            SELECT r.ID_Reserva, r.Fecha_Llegada, r.Fecha_Salida, r.ID_Habitacion,
                   h.Numero_Habitacion, th.Nombre_Tipo,
                   hu.Nombre, hu.Apellido, hu.Email
            FROM Reservas r
            JOIN Habitaciones h ON r.ID_Habitacion = h.ID_Habitacion
            JOIN Tipos_Habitacion th ON h.ID_Tipo_Habitacion = th.ID_Tipo_Habitacion
            JOIN Huespedes hu ON r.ID_Huesped = hu.ID_Huesped
            WHERE r.ID_Reserva = %s AND r.ID_Huesped = %s
        """
        detalles = ejecutar_consulta(query_res, (id_reserva, id_huesped), fetchone=True)

        # Marcar como cancelada
        ejecutar_consulta(
            'UPDATE Reservas SET Estado_Reserva = "Cancelada" WHERE ID_Reserva = %s AND ID_Huesped = %s',
            (id_reserva, id_huesped),
            commit=True
        )

        if detalles:
            # Revertir estado físico de la habitación a Disponible
            ejecutar_consulta(
                'UPDATE Habitaciones SET Estado = "Disponible" WHERE ID_Habitacion = %s',
                (detalles['ID_Habitacion'],),
                commit=True
            )
            # Enviar correo de cancelación en segundo plano
            enviar_correo_cancelacion_async(detalles)

        return jsonify({'mensaje': '¡Reserva cancelada con éxito!'})
    except Exception as err:
        print(f"Error al cancelar: {err}")
        return jsonify({'error': 'Falla al cancelar la reserva.'}), 500

# 10. Suscribirse al Boletín
@app.route('/api/suscribir', methods=['POST'])
def suscribir():
    datos = request.get_json()
    email = datos.get('email')

    if not email:
        return jsonify({'error': 'Ingresa tu correo.'}), 400

    try:
        # Usamos INSERT IGNORE o REPLACE para simular el comportamiento anterior
        ejecutar_consulta(
            """INSERT INTO Suscriptores_Boletin (Email, Activo) 
               VALUES (%s, TRUE) 
               ON DUPLICATE KEY UPDATE Activo = TRUE""",
            (email,),
            commit=True
        )
        # Enviar correo de confirmación de boletín en segundo plano
        enviar_correo_suscripcion_async(email)
        
        return jsonify({'mensaje': '¡Gracias por suscribirte a nuestro boletín!'})
    except Exception as err:
        print(f"Error al suscribir: {err}")
        return jsonify({'error': 'Falla al procesar suscripción.'}), 500


# =====================================================================
# RUTAS API DE ADMINISTRACIÓN (Visuales e Intuitivas)
# =====================================================================

# 1. Obtener todas las habitaciones del hotel (para el administrador)
@app.route('/api/admin/habitaciones', methods=['GET'])
def admin_obtener_habitaciones():
    try:
        query = """
            SELECT h.ID_Habitacion, h.ID_Tipo_Habitacion, h.Numero_Habitacion, h.Estado, h.Piso,
                   th.Nombre_Tipo, th.Precio_Noche, th.Capacidad_Maxima
            FROM Habitaciones h
            JOIN Tipos_Habitacion th ON h.ID_Tipo_Habitacion = th.ID_Tipo_Habitacion
            ORDER BY h.Piso ASC, h.Numero_Habitacion ASC
        """
        habitaciones = ejecutar_consulta(query)
        # Convertir decimales a float para JSON
        for h in habitaciones:
            h['Precio_Noche'] = float(h['Precio_Noche'])
        return jsonify(habitaciones)
    except Exception as err:
        print(f"Error admin al obtener habitaciones: {err}")
        return jsonify({'error': 'Error de base de datos al consultar habitaciones.'}), 500

# 2. Modificar el estado de una habitación (Disponible, Ocupada, Mantenimiento)
@app.route('/api/admin/habitaciones/estado', methods=['POST'])
def admin_actualizar_estado_habitacion():
    datos = request.get_json()
    id_habitacion = datos.get('id_habitacion')
    estado = datos.get('estado')
    
    if not id_habitacion or not estado:
        return jsonify({'error': 'Faltan datos requeridos (id_habitacion, estado).'}), 400
        
    if estado not in ['Disponible', 'Ocupada', 'Mantenimiento', 'Reservada']:
        return jsonify({'error': 'Estado no válido.'}), 400
        
    try:
        ejecutar_consulta(
            'UPDATE Habitaciones SET Estado = %s WHERE ID_Habitacion = %s',
            (estado, id_habitacion),
            commit=True
        )
        return jsonify({'mensaje': '¡Estado de la habitación actualizado con éxito!'})
    except Exception as err:
        print(f"Error admin al cambiar estado: {err}")
        return jsonify({'error': 'Error al actualizar el estado en la base de datos.'}), 500

# 3. Modificar el precio de un tipo de habitación
@app.route('/api/admin/habitaciones/precio', methods=['POST'])
def admin_actualizar_precio_tipo():
    datos = request.get_json()
    id_tipo_habitacion = datos.get('id_tipo_habitacion')
    precio_noche = datos.get('precio_noche')
    
    if not id_tipo_habitacion or precio_noche is None:
        return jsonify({'error': 'Faltan datos requeridos.'}), 400
        
    try:
        precio_val = float(precio_noche)
        if precio_val <= 0:
            return jsonify({'error': 'El precio debe ser mayor a 0.'}), 400
            
        ejecutar_consulta(
            'UPDATE Tipos_Habitacion SET Precio_Noche = %s WHERE ID_Tipo_Habitacion = %s',
            (precio_val, id_tipo_habitacion),
            commit=True
        )
        return jsonify({'mensaje': '¡Precio de habitación actualizado con éxito!'})
    except Exception as err:
        print(f"Error admin al cambiar precio: {err}")
        return jsonify({'error': 'Error al actualizar el precio en la base de datos.'}), 500

# 4. Agregar una nueva habitación física al hotel
@app.route('/api/admin/habitaciones/agregar', methods=['POST'])
def admin_agregar_habitacion():
    datos = request.get_json()
    id_tipo_habitacion = datos.get('id_tipo_habitacion')
    numero_habitacion = datos.get('numero_habitacion')
    estado = datos.get('estado', 'Disponible')
    piso = datos.get('piso')
    
    if not id_tipo_habitacion or not numero_habitacion or not piso:
        return jsonify({'error': 'Faltan datos requeridos para la habitación.'}), 400
        
    try:
        # Validar si ya existe ese número
        existe = ejecutar_consulta('SELECT ID_Habitacion FROM Habitaciones WHERE Numero_Habitacion = %s', (numero_habitacion,))
        if existe:
            return jsonify({'error': f'La habitación número {numero_habitacion} ya existe.'}), 400
            
        id_creado = ejecutar_consulta(
            'INSERT INTO Habitaciones (ID_Tipo_Habitacion, Numero_Habitacion, Estado, Piso) VALUES (%s, %s, %s, %s)',
            (id_tipo_habitacion, numero_habitacion, estado, piso),
            commit=True
        )
        return jsonify({'mensaje': f'Habitación {numero_habitacion} agregada con éxito.', 'id': id_creado}), 201
    except Exception as err:
        print(f"Error admin al agregar habitación: {err}")
        return jsonify({'error': 'Error de base de datos al agregar la habitación.'}), 500

# 5. Obtener todas las reservas de todos los huéspedes (para el administrador)
@app.route('/api/admin/reservas', methods=['GET'])
def admin_obtener_reservas():
    try:
        query = """
            SELECT r.ID_Reserva, r.Fecha_Llegada, r.Fecha_Salida, r.Numero_Adultos, r.Numero_Ninos, r.Estado_Reserva, r.Fecha_Creacion,
                   h.Numero_Habitacion, th.Nombre_Tipo, 
                   COALESCE(r.Precio_Noche_Reservado, th.Precio_Noche) as Precio_Noche,
                   hu.Nombre, hu.Apellido, hu.Email, hu.Telefono,
                   (DATEDIFF(r.Fecha_Salida, r.Fecha_Llegada) * COALESCE(r.Precio_Noche_Reservado, th.Precio_Noche)) as Costo_Hospedaje
            FROM Reservas r
            JOIN Habitaciones h ON r.ID_Habitacion = h.ID_Habitacion
            JOIN Tipos_Habitacion th ON h.ID_Tipo_Habitacion = th.ID_Tipo_Habitacion
            JOIN Huespedes hu ON r.ID_Huesped = hu.ID_Huesped
            ORDER BY r.Fecha_Creacion DESC
        """
        reservas = ejecutar_consulta(query)
        
        resultado_final = []
        for r in reservas:
            if hasattr(r['Fecha_Llegada'], 'strftime'):
                r['Fecha_Llegada'] = r['Fecha_Llegada'].strftime('%Y-%m-%d')
            if hasattr(r['Fecha_Salida'], 'strftime'):
                r['Fecha_Salida'] = r['Fecha_Salida'].strftime('%Y-%m-%d')
            if hasattr(r['Fecha_Creacion'], 'strftime'):
                r['Fecha_Creacion'] = r['Fecha_Creacion'].strftime('%Y-%m-%d %H:%M:%S')
                
            # Cargar servicios asociados
            q_servs = """
                SELECT s.Nombre_Servicio, s.Precio, rs.Cantidad, (s.Precio * rs.Cantidad) as Costo_Servicio
                FROM Reservas_Servicios rs
                JOIN Servicios s ON rs.ID_Servicio = s.ID_Servicio
                WHERE rs.ID_Reserva = %s
            """
            servs = ejecutar_consulta(q_servs, (r['ID_Reserva'],))
            
            costo_servs_total = 0.0
            for s in servs:
                costo_servs_total += float(s['Costo_Servicio'] or 0.0)
                s['Precio'] = float(s['Precio'])
                s['Costo_Servicio'] = float(s['Costo_Servicio'])
                
            costo_hospedaje = float(r['Costo_Hospedaje'])
            costo_total = costo_hospedaje + costo_servs_total
            
            r['Precio_Noche'] = float(r['Precio_Noche'])
            r['Costo_Hospedaje'] = costo_hospedaje
            r['Costo_Total'] = costo_total
            r['ServiciosAdicionales'] = servs
            resultado_final.append(r)
            
        return jsonify(resultado_final)
    except Exception as err:
        print(f"Error admin al obtener reservas: {err}")
        return jsonify({'error': 'Error de base de datos al obtener historial completo.'}), 500

# 6. Actualizar el estado de una reserva
@app.route('/api/admin/reservas/estado', methods=['POST'])
def admin_actualizar_estado_reserva():
    datos = request.get_json()
    id_reserva = datos.get('id_reserva')
    estado = datos.get('estado')
    
    if not id_reserva or not estado:
        return jsonify({'error': 'Faltan datos requeridos (id_reserva, estado).'}), 400
        
    if estado not in ['Pendiente', 'Confirmada', 'Cancelada', 'Finalizada']:
        return jsonify({'error': 'Estado de reserva no válido.'}), 400
        
    try:
        # Obtener datos de la reserva antes de actualizar para el envío de correo si es cancelación
        query_res = """
            SELECT r.ID_Reserva, r.Fecha_Llegada, r.Fecha_Salida, r.ID_Habitacion,
                   h.Numero_Habitacion, th.Nombre_Tipo,
                   hu.Nombre, hu.Apellido, hu.Email
            FROM Reservas r
            JOIN Habitaciones h ON r.ID_Habitacion = h.ID_Habitacion
            JOIN Tipos_Habitacion th ON h.ID_Tipo_Habitacion = th.ID_Tipo_Habitacion
            JOIN Huespedes hu ON r.ID_Huesped = hu.ID_Huesped
            WHERE r.ID_Reserva = %s
        """
        detalles = ejecutar_consulta(query_res, (id_reserva,), fetchone=True)

        ejecutar_consulta(
            'UPDATE Reservas SET Estado_Reserva = %s WHERE ID_Reserva = %s',
            (estado, id_reserva),
            commit=True
        )
        
        # Sincronizar estado de habitación física y enviar correo de cancelación
        if detalles:
            nuevo_estado_hab = 'Disponible' if estado in ['Cancelada', 'Finalizada'] else 'Reservada'
            ejecutar_consulta(
                'UPDATE Habitaciones SET Estado = %s WHERE ID_Habitacion = %s',
                (nuevo_estado_hab, detalles['ID_Habitacion']),
                commit=True
            )
            if estado == 'Cancelada':
                enviar_correo_cancelacion_async(detalles)
            
        return jsonify({'mensaje': '¡Estado de reserva actualizado con éxito!'})
    except Exception as err:
        print(f"Error admin al actualizar estado de reserva: {err}")
        return jsonify({'error': 'Error de base de datos al actualizar la reserva.'}), 500

# 7. Obtener lista de todos los servicios para admin (incluyendo inactivos)
@app.route('/api/admin/servicios', methods=['GET'])
def admin_obtener_servicios():
    try:
        servicios = ejecutar_consulta('SELECT * FROM Servicios')
        for s in servicios:
            s['Precio'] = float(s['Precio'])
        return jsonify(servicios)
    except Exception as err:
        print(f"Error admin al obtener servicios: {err}")
        return jsonify({'error': 'Error de base de datos al obtener el catálogo de servicios.'}), 500

# 8. Modificar precio y disponibilidad de servicios
@app.route('/api/admin/servicios/actualizar', methods=['POST'])
def admin_actualizar_servicio():
    datos = request.get_json()
    id_servicio = datos.get('id_servicio')
    precio = datos.get('precio')
    disponible = datos.get('disponible')
    
    if not id_servicio or precio is None or disponible is None:
        return jsonify({'error': 'Faltan datos requeridos.'}), 400
        
    try:
        precio_val = float(precio)
        if precio_val < 0:
            return jsonify({'error': 'El precio no puede ser negativo.'}), 400
            
        ejecutar_consulta(
            'UPDATE Servicios SET Precio = %s, Disponible = %s WHERE ID_Servicio = %s',
            (precio_val, int(disponible), id_servicio),
            commit=True
        )
        return jsonify({'mensaje': '¡Servicio actualizado con éxito!'})
    except Exception as err:
        print(f"Error admin al actualizar servicio: {err}")
        return jsonify({'error': 'Error de base de datos al actualizar el servicio.'}), 500

# 9. Obtener todos los testimonios no eliminados para admin
@app.route('/api/admin/testimonios', methods=['GET'])
def admin_obtener_testimonios():
    try:
        query = """
            SELECT t.ID_Testimonio, t.Comentario, t.Calificacion_Estrellas, t.Fecha_Publicacion, t.Aprobado,
                   h.Nombre, h.Apellido, h.Email
            FROM Testimonios t
            JOIN Huespedes h ON t.ID_Huesped = h.ID_Huesped
            WHERE t.Eliminado IS NULL OR t.Eliminado = FALSE
            ORDER BY t.Fecha_Publicacion DESC
        """
        testimonios = ejecutar_consulta(query)
        for t in testimonios:
            if hasattr(t['Fecha_Publicacion'], 'strftime'):
                t['Fecha_Publicacion'] = t['Fecha_Publicacion'].strftime('%Y-%m-%d')
            t['Aprobado'] = bool(t['Aprobado'])
        return jsonify(testimonios)
    except Exception as err:
        print(f"Error admin al obtener testimonios: {err}")
        return jsonify({'error': 'Error de base de datos al obtener testimonios.'}), 500

# 10. Actualizar comentario y estado de aprobación de un testimonio
@app.route('/api/admin/testimonios/actualizar', methods=['POST'])
def admin_actualizar_testimonio():
    datos = request.get_json()
    id_testimonio = datos.get('id_testimonio')
    comentario = datos.get('comentario')
    aprobado = datos.get('aprobado')
    
    if not id_testimonio or comentario is None or aprobado is None:
        return jsonify({'error': 'Faltan datos requeridos.'}), 400
        
    try:
        ejecutar_consulta(
            'UPDATE Testimonios SET Comentario = %s, Aprobado = %s WHERE ID_Testimonio = %s',
            (comentario, int(aprobado), id_testimonio),
            commit=True
        )
        return jsonify({'mensaje': '¡Testimonio actualizado con éxito!'})
    except Exception as err:
        print(f"Error admin al actualizar testimonio: {err}")
        return jsonify({'error': 'Error de base de datos al actualizar el testimonio.'}), 500

# 11. Eliminar testimonio (Soft Delete)
@app.route('/api/admin/testimonios/eliminar', methods=['POST'])
def admin_eliminar_testimonio():
    datos = request.get_json()
    id_testimonio = datos.get('id_testimonio')
    
    if not id_testimonio:
        return jsonify({'error': 'Falta el ID del testimonio.'}), 400
        
    try:
        ejecutar_consulta(
            'UPDATE Testimonios SET Eliminado = TRUE WHERE ID_Testimonio = %s',
            (id_testimonio,),
            commit=True
        )
        return jsonify({'mensaje': '¡Testimonio ocultado/eliminado con éxito!'})
    except Exception as err:
        print(f"Error admin al eliminar testimonio: {err}")
        return jsonify({'error': 'Error de base de datos al eliminar el testimonio.'}), 500


# =====================================================================
# INICIO DEL SERVIDOR
# =====================================================================
if __name__ == '__main__':
    puerto = int(os.getenv("PORT", 5000))
    print(f"====================================================")
    print(f" Servidor de Hotel Riviera corriendo correctamente")
    print(f" Sitio web disponible en: http://localhost:{puerto}")
    print(f"====================================================")
    app.run(debug=True, port=puerto)
