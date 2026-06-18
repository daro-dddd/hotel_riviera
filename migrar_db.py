# migrar_db.py
# Script de automatización para migrar e inicializar la base de datos SQL en Railway u otros hostings.
# Creado para ejecutar de manera sencilla el script 'base_de_datos.sql' en un servidor MySQL remoto.

import os
import sys
import mysql.connector
from dotenv import load_dotenv

# Cargar variables locales si existen (.env)
load_dotenv()

def migrar():
    print("=====================================================================")
    print("   INICIANDO MIGRACIÓN AUTOMÁTICA DE BASE DE DATOS EN LA NUBE")
    print("=====================================================================")
    
    # Intentar obtener variables de entorno de conexión
    # Railway provee la variable MYSQL_URL o individuales: MYSQLHOST, MYSQLPORT, MYSQLUSER, MYSQLPASSWORD, MYSQLDATABASE
    url_db = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")
    
    config = {}
    if url_db and url_db.startswith("mysql://"):
        print("[Info] Detectada cadena de conexión MYSQL_URL. Parseando credenciales...")
        try:
            # Parsear URL de formato: mysql://usuario:contraseña@host:puerto/nombre_bd
            url_part = url_db.replace("mysql://", "")
            user_pass, host_port_db = url_part.split("@")
            user, password = user_pass.split(":")
            host_port, database = host_port_db.split("/")
            
            # Quitar parámetros adicionales de la URL si existen (?ssl-mode=...)
            if "?" in database:
                database = database.split("?")[0]
                
            host, port = host_port.split(":")
            
            config = {
                "user": user,
                "password": password,
                "host": host,
                "port": int(port),
                "database": database
            }
        except Exception as e:
            print(f"[Error] No se pudo parsear la URL de conexión: {e}")
            sys.exit(1)
    else:
        # Fallback a variables individuales (estándar en .env y Railway)
        config = {
            "database": os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE"),
            "user":     os.getenv("DB_USER") or os.getenv("MYSQLUSER"),
            "password": os.getenv("DB_PASSWORD") or os.getenv("MYSQLPASSWORD"),
            "host":     os.getenv("DB_HOST") or os.getenv("MYSQLHOST", "localhost"),
            "port":     int(os.getenv("DB_PORT") or os.getenv("MYSQLPORT", 3306))
        }

    # Validaciones de seguridad de credenciales
    if not config["user"] or not config["password"] or not config["host"]:
        print("[Error] No se encontraron las credenciales de conexión de MySQL.")
        print("Asegúrate de configurar tu archivo .env o las variables de entorno en el servidor.")
        print("Variables requeridas: DB_USER, DB_PASSWORD, DB_HOST, DB_NAME (o MYSQLUSER, MYSQLPASSWORD, etc.)")
        sys.exit(1)

    print(f"[Info] Conectando a servidor MySQL en {config['host']}:{config['port']}...")
    
    try:
        # Intentar conexión directa
        conn = mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        print(f"[Advertencia] Fallo de conexión directa: {err}")
        print("[Info] Intentando conectar sin base de datos específica para crearla...")
        try:
            config_no_db = config.copy()
            db_target = config_no_db.pop("database", None)
            
            conn = mysql.connector.connect(**config_no_db)
            cursor = conn.cursor()
            
            if db_target:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_target}")
                print(f"[Éxito] Base de datos '{db_target}' creada con éxito.")
                conn.database = db_target
            else:
                print("[Error] No se ha especificado el nombre de la base de datos.")
                sys.exit(1)
        except Exception as e:
            print(f"[Error Crítico] No fue posible conectarse al servidor MySQL: {e}")
            sys.exit(1)

    cursor = conn.cursor()
    print("[Éxito] ¡Conexión establecida con el servidor MySQL remoto!")
    
    # Localizar archivo SQL
    sql_file_path = "base_de_datos.sql"
    if not os.path.exists(sql_file_path):
        print(f"[Error] No se encontró el archivo '{sql_file_path}' en el directorio actual.")
        sys.exit(1)
        
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Procesar archivo SQL línea por línea para dividirlo en comandos individuales
    statements = []
    current_statement = []
    
    for line in sql_content.splitlines():
        stripped_line = line.strip()
        
        # Omitir comentarios de SQL y líneas vacías
        if not stripped_line or stripped_line.startswith("--") or stripped_line.startswith("#") or stripped_line.startswith("/*"):
            continue
            
        # Omitir comandos locales de creación y selección que fallan en bases de datos gestionadas de la nube
        if stripped_line.upper().startswith("CREATE DATABASE") or stripped_line.upper().startswith("USE "):
            continue
            
        current_statement.append(line)
        
        # Si la línea termina en punto y coma, significa fin del comando
        if stripped_line.endswith(";"):
            statements.append("\n".join(current_statement))
            current_statement = []
            
    print(f"[Info] Procesadas {len(statements)} sentencias SQL listas para ejecutar.")
    
    # Ejecución secuencial de los comandos
    exitos = 0
    errores = 0
    
    for idx, stmt in enumerate(statements, 1):
        if not stmt.strip():
            continue
        try:
            cursor.execute(stmt)
            conn.commit()
            exitos += 1
        except mysql.connector.Error as err:
            print(f"\n[Error en Comando #{idx}]")
            print(stmt)
            print(f"Detalle del fallo de MySQL: {err}")
            print("-" * 60)
            errores += 1
            
    cursor.close()
    conn.close()
    
    print("\n=====================================================================")
    print("   MIGRACIÓN DE BASE DE DATOS FINALIZADA")
    print("=====================================================================")
    print(f" -> Comandos exitosos: {exitos}")
    print(f" -> Comandos fallidos: {errores}")
    
    if errores == 0:
        print("\n¡La base de datos en Railway se ha inicializado a la perfección!")
    else:
        print("\nEl proceso terminó con algunos errores. Verifica los reportes arriba.")

if __name__ == "__main__":
    migrar()
