# Guía de Despliegue en la Nube - Hotel Riviera

Esta guía describe detalladamente los pasos para subir la base de datos MySQL y la aplicación web de Flask a servicios en la nube de forma gratuita o de bajo costo (como **Railway**, **Clever Cloud** o **Render**).

---

## Parte 1: Subir la Base de Datos a la Nube

Para tener la base de datos accesible desde cualquier lugar, se debe crear una base de datos MySQL gestionada en la nube.

### Opción A: Despliegue en Railway (Recomendado)
1. Crea una cuenta en [Railway.app](https://railway.app).
2. Haz clic en **New Project** (Nuevo proyecto).
3. Selecciona **Provision MySQL** (Proveer MySQL).
4. Railway creará un contenedor de base de datos MySQL en segundos.
5. Ve a la pestaña **Variables** o **Connect** del servicio MySQL en Railway y copia la cadena de conexión o los datos individuales:
   - **Host** (e.g. `mysql.railway.internal` o el host externo provisto)
   - **Port** (normalmente `3306`)
   - **User** (e.g. `root`)
   - **Password**
   - **Database / Schema** (normalmente `railway`)
   - **MYSQL_URL** (Cadena completa como `mysql://root:contraseña@host:puerto/railway`)

### Opción B: Despliegue en Clever Cloud (Alternativa 100% gratuita)
1. Regístrate en [Clever Cloud](https://www.clever-cloud.com).
2. Haz clic en **Create** -> **An Addon**.
3. Elige **MySQL** (selecciona el plan gratuito "Shared").
4. Clever Cloud te mostrará de inmediato las credenciales de conexión (`Host`, `Database`, `User`, `Password`, `Port`).

---

## Parte 2: Migrar el Esquema y los Datos Semilla

El archivo `migrar_db.py` está diseñado para leer el esquema de `base_de_datos.sql` y ejecutarlo directamente en tu servidor de la nube de forma automatizada.

### Instrucciones para la migración:
1. Abre el archivo `.env` local en tu computadora.
2. Modifica temporalmente las variables de conexión con los datos que te entregó tu proveedor en la nube:
   ```env
   DB_HOST=tu_host_en_la_nube.com
   DB_USER=usuario_nube
   DB_PASSWORD=contraseña_nube
   DB_NAME=nombre_bd_nube
   DB_PORT=puerto_nube (e.g. 3306)
   ```
   *O bien, si tienes una URL completa en Railway, puedes configurar la variable:*
   ```env
   MYSQL_URL=mysql://usuario:contraseña@host:puerto/nombre_bd
   ```
3. Ejecuta el script de migración desde tu consola:
   ```bash
   python migrar_db.py
   ```
4. El script se conectará al servidor de la nube, creará todas las tablas (`Huespedes`, `Habitaciones`, `Reservas`, etc.) e insertará los datos iniciales, incluyendo las 3 nuevas habitaciones y el administrador (`admin@hotelriviera.com`).
5. ¡Listo! Tu base de datos en la nube ya está inicializada. Ahora regresa el archivo `.env` local a sus valores anteriores si quieres seguir probando en tu máquina local.

---

## Parte 3: Desplegar el Servidor Flask a la Nube

Para subir el servidor Python y el frontend, utilizaremos un servicio como **Render** o **Railway** conectado a tu repositorio de GitHub.

### Paso 1: Subir tu código a GitHub
1. Inicializa un repositorio Git local si no lo has hecho:
   ```bash
   git init
   git add .
   git commit -m "Añadir panel administrador y nuevas habitaciones"
   ```
2. Crea un repositorio en tu cuenta de GitHub (e.g., `hotel-riviera`).
3. Sube tu código a GitHub siguiendo las instrucciones que te proporcione la página:
   ```bash
   git remote add origin https://github.com/tu_usuario/hotel-riviera.git
   git branch -M main
   git push -u origin main
   ```

### Paso 2: Configurar el servicio en Render (Recomendado para el backend)
1. Regístrate en [Render.com](https://render.com).
2. Haz clic en el botón **New +** y selecciona **Web Service**.
3. Conecta tu cuenta de GitHub y selecciona el repositorio de tu proyecto (`hotel-riviera`).
4. Configura los parámetros del servicio:
   - **Name**: `hotel-riviera`
   - **Environment**: `Python`
   - **Region**: Selecciona la más cercana (e.g., Oregon o Ohio).
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app` (Render detectará automáticamente el archivo `Procfile` si ya existe).
5. Haz clic en **Advanced** para agregar las **Variables de Entorno (Environment Variables)**:
   - Deberás agregar las credenciales de la base de datos de la nube que configuraste en la Parte 1:
     - `DB_HOST` = `tu_host_de_la_nube`
     - `DB_USER` = `tu_usuario_de_la_nube`
     - `DB_PASSWORD` = `tu_contraseña_de_la_nube`
     - `DB_NAME` = `tu_base_de_datos_de_la_nube`
     - `DB_PORT` = `3306` (o el puerto que corresponda)
     - `PORT` = `10000` (puerto que Render asignará automáticamente para escuchar peticiones).
6. Haz clic en **Create Web Service**.
7. Render descargará el código de GitHub, instalará las dependencias y encenderá el servidor de Flask.
8. Una vez terminado el despliegue ("Live"), Render te proporcionará una URL pública (e.g., `https://hotel-riviera.onrender.com`).
9. ¡Felicidades! Al ingresar a esa URL podrás interactuar con la aplicación, hacer reservas reales y gestionar todo desde la nube.
