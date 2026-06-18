-- =====================================================================
-- SCRIPT DE CREACIÓN DE BASE DE DATOS - HOTEL RIVIERA
-- =====================================================================
-- Propósito: Inicializar la base de datos MySQL local para el proyecto.
-- Este archivo puede ser ejecutado directamente en MySQL Workbench.
-- =====================================================================

-- 1. Crear base de datos si no existe y seleccionarla
CREATE DATABASE IF NOT EXISTS HotelDB;
USE HotelDB;

-- 2. Limpieza de tablas existentes para reinstalación limpia (opcional, en orden de dependencias)
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS Reservas_Servicios;
DROP TABLE IF EXISTS Suscriptores_Boletin;
DROP TABLE IF EXISTS Testimonios;
DROP TABLE IF EXISTS Servicios;
DROP TABLE IF EXISTS Reservas;
DROP TABLE IF EXISTS Habitaciones;
DROP TABLE IF EXISTS Tipos_Habitacion;
DROP TABLE IF EXISTS Huespedes;
SET FOREIGN_KEY_CHECKS = 1;

-- 3. Creación de la Tabla: Huespedes
-- Almacena la información de los usuarios registrados para hacer reservas.
CREATE TABLE Huespedes (
    ID_Huesped INT AUTO_INCREMENT PRIMARY KEY,
    Nombre VARCHAR(50) NOT NULL,
    Apellido VARCHAR(50) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    Contrasena VARCHAR(255) NOT NULL, -- Columna añadida para manejar el login de la web
    Telefono VARCHAR(20) UNIQUE,
    URL_Foto_Perfil VARCHAR(255) NULL,
    Fecha_Registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_email CHECK (Email LIKE '%@%.%')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Creación de la Tabla: Tipos_Habitacion
-- Define categorías de habitaciones con su capacidad y precio.
CREATE TABLE Tipos_Habitacion (
    ID_Tipo_Habitacion INT AUTO_INCREMENT PRIMARY KEY,
    Nombre_Tipo VARCHAR(50) NOT NULL UNIQUE,
    Descripcion TEXT NULL,
    Capacidad_Maxima INT NOT NULL CHECK (Capacidad_Maxima > 0),
    Precio_Noche DECIMAL(10,2) NOT NULL CHECK (Precio_Noche > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Creación de la Tabla: Habitaciones
-- Habitaciones físicas del hotel.
CREATE TABLE Habitaciones (
    ID_Habitacion INT AUTO_INCREMENT PRIMARY KEY,
    ID_Tipo_Habitacion INT NOT NULL,
    Numero_Habitacion VARCHAR(10) NOT NULL UNIQUE,
    Estado ENUM('Disponible', 'Ocupada', 'Mantenimiento') DEFAULT 'Disponible',
    Piso INT NOT NULL CHECK (Piso > 0),
    FOREIGN KEY (ID_Tipo_Habitacion) REFERENCES Tipos_Habitacion(ID_Tipo_Habitacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Creación de la Tabla: Reservas
-- Registra reservas de habitaciones.
CREATE TABLE Reservas (
    ID_Reserva INT AUTO_INCREMENT PRIMARY KEY,
    ID_Huesped INT NOT NULL,
    ID_Habitacion INT NOT NULL,
    Fecha_Llegada DATE NOT NULL,
    Fecha_Salida DATE NOT NULL,
    Numero_Adultos INT NOT NULL CHECK (Numero_Adultos > 0),
    Numero_Ninos INT DEFAULT 0 CHECK (Numero_Ninos >= 0),
    Estado_Reserva ENUM('Pendiente', 'Confirmada', 'Cancelada', 'Finalizada') DEFAULT 'Pendiente',
    Fecha_Creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ID_Huesped) REFERENCES Huespedes(ID_Huesped),
    FOREIGN KEY (ID_Habitacion) REFERENCES Habitaciones(ID_Habitacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Creación de la Tabla: Servicios
-- Catálogo de servicios adicionales.
CREATE TABLE Servicios (
    ID_Servicio INT AUTO_INCREMENT PRIMARY KEY,
    Nombre_Servicio VARCHAR(100) NOT NULL UNIQUE,
    Descripcion_Corta VARCHAR(255) NULL,
    Imagen_URL VARCHAR(255) NULL,
    Precio DECIMAL(10,2) NOT NULL CHECK (Precio >= 0),
    Disponible BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Creación de la Tabla: Testimonios
-- Reseñas de clientes para el hotel.
CREATE TABLE Testimonios (
    ID_Testimonio INT AUTO_INCREMENT PRIMARY KEY,
    ID_Huesped INT NOT NULL,
    Comentario TEXT NOT NULL,
    Calificacion_Estrellas INT NOT NULL CHECK (Calificacion_Estrellas BETWEEN 1 AND 5),
    Fecha_Publicacion DATE DEFAULT (CURRENT_DATE),
    Aprobado BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (ID_Huesped) REFERENCES Huespedes(ID_Huesped)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Creación de la Tabla: Suscriptores_Boletin
-- Correos del newsletter.
CREATE TABLE Suscriptores_Boletin (
    ID_Suscriptor INT AUTO_INCREMENT PRIMARY KEY,
    Email VARCHAR(100) NOT NULL UNIQUE,
    Fecha_Suscripcion DATE DEFAULT (CURRENT_DATE),
    Activo BOOLEAN DEFAULT TRUE,
    CONSTRAINT chk_email_boletin CHECK (Email LIKE '%@%.%')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Creación de la Tabla: Reservas_Servicios (Relación Muchos a Muchos)
-- Relaciona servicios extras con las reservas del huésped.
CREATE TABLE Reservas_Servicios (
    ID_Reserva INT NOT NULL,
    ID_Servicio INT NOT NULL,
    Cantidad INT DEFAULT 1 CHECK (Cantidad > 0),
    Fecha_Servicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID_Reserva, ID_Servicio),
    FOREIGN KEY (ID_Reserva) REFERENCES Reservas(ID_Reserva) ON DELETE CASCADE,
    FOREIGN KEY (ID_Servicio) REFERENCES Servicios(ID_Servicio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- INSERCIÓN DE DATOS INICIALES DE PRUEBA
-- =====================================================================

-- Huesped de prueba (contraseña original: contrasena123 y secreto456, ahora almacenadas como hashes seguros)
-- NOTA: Las contraseñas se almacenan como hashes generados por werkzeug.security para garantizar la seguridad.
INSERT INTO Huespedes (Nombre, Apellido, Email, Contrasena, Telefono) VALUES
('Carlos', 'Martinez', 'carlos.martinez@mail.com', 'scrypt:32768:8:1$qWuztHvEKYpIQvWS$7b3f818ceab7ae04849371641f1d76cffdc3b7bf9d19f8f28453d902308639bbd9941026ddc9212963752c0a6a05809babb3c82f532d331f089c87ecd3290707', '+52 555-123-4567'),
('Laura', 'Gomez', 'laura.gomez@mail.com', 'scrypt:32768:8:1$U3QT9SvRGFWJKJzG$fe2c1eda339c8e7120cfc0530126c6f4237216dfe83603d35770d29e9244a7ac4393283bb90c4b92aab757590f8a4d2169e245299c428add63ce54dc1d761d5d', '+52 555-987-6543');

-- Tipos de Habitaciones
INSERT INTO Tipos_Habitacion (Nombre_Tipo, Descripcion, Capacidad_Maxima, Precio_Noche) VALUES
('Habitación Doble', 'Acogedora habitación con dos camas matrimoniales y vista parcial a los jardines.', 4, 120.00),
('Suite Deluxe', 'Elegante y espaciosa suite con cama King Size, sala de estar independiente y terraza privada.', 2, 200.00),
('Habitación Familiar', 'Ideal para grupos o familias, equipada con tres camas matrimoniales y un área de comedor pequeña.', 6, 180.00),
('Suite Frente al Mar', 'La máxima experiencia de lujo: balcón privado directo a la playa con jacuzzi exterior.', 4, 250.00),
('Habitación Sencilla', 'Espacio acogedor y funcional con cama individual, ideal para viajeros solitarios o estancias de negocios.', 1, 50.00),
('Suite Presidencial Extra Lujo', 'La joya del hotel: dos niveles, terraza panorámica, jacuzzi, piscina infinita privada y acabados de mármol premium.', 6, 600.00),
('Villa Vista al Mar', 'Villa exclusiva e independiente a unos pasos de la playa, con jardín tropical privado y piscina propia.', 4, 400.00),
('Habitación Individual Ejecutiva', 'Diseñada para viajes de negocios con cama Queen, escritorio ergonómico y acceso de alta velocidad.', 2, 90.00),
('Penthouse Vista al Cielo', 'Espectacular suite en el último piso con paredes de cristal, vistas de 360 grados y telescopio para ver las estrellas.', 4, 350.00);

-- Habitaciones Físicas
INSERT INTO Habitaciones (ID_Tipo_Habitacion, Numero_Habitacion, Estado, Piso) VALUES
(1, '101', 'Disponible', 1),
(1, '102', 'Disponible', 1),
(1, '103', 'Ocupada', 1),
(2, '201', 'Disponible', 2),
(2, '202', 'Mantenimiento', 2),
(3, '301', 'Disponible', 3),
(3, '302', 'Disponible', 3),
(4, '401', 'Disponible', 4),
(5, '104', 'Disponible', 1),
(5, '105', 'Disponible', 1),
(6, '501', 'Disponible', 5),
(7, '601', 'Disponible', 1),
(7, '602', 'Disponible', 1),
(8, '203', 'Disponible', 2),
(8, '204', 'Disponible', 2),
(9, '701', 'Disponible', 7);

-- Catálogo de Servicios
INSERT INTO Servicios (Nombre_Servicio, Descripcion_Corta, Imagen_URL, Precio, Disponible) VALUES
('Piscina de Borde Infinito', 'Acceso a la piscina climatizada con camastros y bar exterior.', 'piscina.png', 0.00, TRUE),
('Spa & Wellness Center', 'Masajes relajantes, tratamientos corporales y sauna de vapor.', 'spa.png', 500.00, TRUE),
('Restaurante Gourmet Riviera', 'Servicio a la carta con alta cocina internacional y bebidas de cortesía.', 'restaurante.png', 350.00, TRUE),
('Wi-Fi de Alta Velocidad', 'Conexión a internet ilimitada en áreas comunes y habitaciones.', 'wifi.png', 0.00, TRUE),
('Desayuno Buffet Premium', 'Gran variedad de panes artesanales, jugos, frutas y platillos tradicionales calientes.', 'desayuno.png', 150.00, TRUE),
('Tour de Avistamiento de Ballenas', 'Emocionante excursión en lancha para observar ballenas jorobadas en su hábitat natural.', 'ballenas.png', 80.00, TRUE),
('Clase de Surf Privada', 'Aprende a dominar las olas con un instructor certificado y equipo personalizado incluido.', 'surf.png', 50.00, TRUE),
('Cena Romántica en la Playa', 'Disfruta de una cena exclusiva de tres tiempos a la luz de las velas frente al mar.', 'cena.png', 120.00, TRUE);

-- Testimonios
INSERT INTO Testimonios (ID_Huesped, Comentario, Calificacion_Estrellas, Aprobado) VALUES
(1, 'Una estancia maravillosa, el personal de Hotel Riviera fue muy atento y las habitaciones frente al mar tienen una vista inmejorable. Sin duda volveremos.', 5, TRUE),
(2, 'Excelente comida en el restaurante gourmet y los masajes en el spa fueron súper relajantes. Recomendado 100% para parejas.', 4, TRUE);

-- Suscriptores de Boletín
INSERT INTO Suscriptores_Boletin (Email, Activo) VALUES
('cliente.interesado@gmail.com', TRUE),
('viajero.frecuente@outlook.com', TRUE);
