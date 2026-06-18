const TIPO_CAMBIO = 20.00;

// Variables globales para llevar el estado de la aplicación
let usuarioLogueado = null;
let catalogoHabitaciones = [];
let catalogoServicios = [];
let habitacionSeleccionada = null; // Para guardar cuál habitación se va a reservar

// Al cargar la página, ejecutamos la inicialización
document.addEventListener('DOMContentLoaded', () => {
    verificarSesionLocal();
    cargarHabitaciones();
    cargarServicios();
    cargarTestimonios();
    
    // Configurar fechas mínimas por defecto en los buscadores (hoy y mañana)
    const hoy = obtenerFechaFormateada(0);
    const mañana = obtenerFechaFormateada(1);
    
    const inputLlegada = document.getElementById('buscar-llegada');
    const inputSalida = document.getElementById('buscar-salida');
    if (inputLlegada && inputSalida) {
        inputLlegada.min = hoy;
        inputLlegada.value = hoy;
        inputSalida.min = mañana;
        inputSalida.value = mañana;
    }

    // Configurar apertura automática de calendarios al hacer clic o focus
    const inputsFechas = ['buscar-llegada', 'buscar-salida', 'res-form-llegada', 'res-form-salida'];
    inputsFechas.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('click', () => {
                try { input.showPicker(); } catch (e) {}
            });
            input.addEventListener('focus', () => {
                try { input.showPicker(); } catch (e) {}
            });
        }
    });

    inicializarGaleriaLightbox();
});

// =====================================================================
// HELPER: OBTENER FECHAS EN FORMATO YYYY-MM-DD
// =====================================================================
function obtenerFechaFormateada(diasAdicionales = 0) {
    const fecha = new Date();
    fecha.setDate(fecha.getDate() + diasAdicionales);
    const anio = fecha.getFullYear();
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const dia = String(fecha.getDate()).padStart(2, '0');
    return `${anio}-${mes}-${dia}`;
}

// =====================================================================
// 1. GESTIÓN DE SESIÓN (LOGIN / REGISTRO / LOGOUT)
// =====================================================================

// Verifica si hay un usuario guardado en el navegador (localStorage)
function verificarSesionLocal() {
    const datosGuardados = localStorage.getItem('usuario_riviera');
    if (datosGuardados) {
        usuarioLogueado = JSON.parse(datosGuardados);
        actualizarMenuUsuario(true);
    } else {
        actualizarMenuUsuario(false);
    }
}

// Cambia los botones del menú de navegación dependiendo de si hay sesión iniciada
function actualizarMenuUsuario(sesionActiva) {
    const contenedorUsuario = document.getElementById('menu-usuario');
    const cajaTestimonioForm = document.getElementById('formulario-testimonio-contenedor');
    const invitacionLoginTest = document.getElementById('formulario-testimonio-invitacion');
    
    if (sesionActiva && usuarioLogueado) {
        // Si está logueado, mostramos su nombre y botón de cerrar sesión
        contenedorUsuario.innerHTML = `
            <button class="btn btn-usuario-panel" onclick="abrirPanelUsuario()">
                <i class="fa-solid fa-circle-user"></i> Hola, ${usuarioLogueado.nombre}
            </button>
            <button class="btn btn-rojo" onclick="cerrarSesion()">
                <i class="fa-solid fa-right-from-bracket"></i> Salir
            </button>
        `;
        // Mostramos el formulario de testimonios y ocultamos el banner de invitación
        if (cajaTestimonioForm) cajaTestimonioForm.classList.remove('oculto');
        if (invitacionLoginTest) invitacionLoginTest.classList.add('oculto');
    } else {
        // Si no, mostramos el botón de iniciar sesión
        contenedorUsuario.innerHTML = `
            <button class="btn btn-primario" onclick="abrirModal('modal-login')">
                <i class="fa-solid fa-user-tie"></i> Iniciar Sesión
            </button>
        `;
        if (cajaTestimonioForm) cajaTestimonioForm.classList.add('oculto');
        if (invitacionLoginTest) invitacionLoginTest.classList.remove('oculto');
    }
}

// Iniciar sesión llamando a la API
async function ejecutarLogin(event) {
    event.preventDefault(); // Evitamos que la página se recargue sola
    
    const email = document.getElementById('login-email').value.trim().toLowerCase();
    const contrasena = document.getElementById('login-password').value;
    
    try {
        const respuesta = await fetch('/api/iniciar-sesion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, contrasena })
        });
        
        const datos = await respuesta.json();
        
        if (!respuesta.ok) {
            // Sacudida visual del modal de login ante cualquier error
            const modalTarjeta = document.querySelector('#modal-login .modal-tarjeta');
            if (modalTarjeta) {
                modalTarjeta.classList.add('shake');
                setTimeout(() => modalTarjeta.classList.remove('shake'), 600);
            }
            
            if (respuesta.status === 404) {
                if (confirm('Este correo electrónico no está registrado. ¿Deseas crear una cuenta nueva?')) {
                    cambiarModal('modal-login', 'modal-registro');
                }
            } else {
                alert(datos.error || 'Correo electrónico o contraseña incorrectos.');
            }
            return;
        }
        
        // Guardamos los datos en localStorage
        localStorage.setItem('usuario_riviera', JSON.stringify(datos.usuario));
        usuarioLogueado = datos.usuario;
        
        actualizarMenuUsuario(true);
        cerrarModal('modal-login');
        
        // Limpiamos los campos
        document.getElementById('formulario-login').reset();
        
        alert(`¡Bienvenido de nuevo, ${usuarioLogueado.nombre}!`);
        
    } catch (error) {
        console.error('Error de login:', error);
        alert('No se pudo conectar con el servidor.');
    }
}

// Registrar un nuevo huésped
async function ejecutarRegistro(event) {
    event.preventDefault();
    
    const nombre = document.getElementById('reg-nombre').value;
    const apellido = document.getElementById('reg-apellido').value;
    const email = document.getElementById('reg-email').value.trim().toLowerCase();
    const contrasena = document.getElementById('reg-password').value;
    const telefono = document.getElementById('reg-telefono').value;
    
    try {
        const respuesta = await fetch('/api/registrar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre, apellido, email, contrasena, telefono })
        });
        
        const datos = await respuesta.json();
        
        if (!respuesta.ok) {
            alert(datos.error || 'Ocurrió un error en el registro.');
            return;
        }
        
        // Iniciamos sesión automáticamente con el usuario recién creado
        localStorage.setItem('usuario_riviera', JSON.stringify(datos.usuario));
        usuarioLogueado = datos.usuario;
        
        actualizarMenuUsuario(true);
        cerrarModal('modal-registro');
        document.getElementById('formulario-registro').reset();
        
        alert('¡Cuenta creada correctamente! Iniciando sesión...');
        
    } catch (error) {
        console.error('Error de registro:', error);
        alert('No se pudo completar el registro.');
    }
}

// Cerrar sesión
function cerrarSesion() {
    if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
        localStorage.removeItem('usuario_riviera');
        usuarioLogueado = null;
        actualizarMenuUsuario(false);
        alert('Sesión cerrada correctamente.');
        window.location.reload(); // Recargamos para limpiar cualquier estado visible de reservas
    }
}


// =====================================================================
// 2. MODALES (ABRIR, CERRAR, CAMBIAR)
// =====================================================================

function abrirModal(idModal) {
    const modal = document.getElementById(idModal);
    if (modal) {
        modal.classList.add('activo');
        document.body.style.overflow = 'hidden'; // Evita scroll de fondo
        
        // Limpiar formularios al abrir para no mostrar datos anteriores
        if (idModal === 'modal-login') {
            const loginForm = document.getElementById('formulario-login');
            if (loginForm) loginForm.reset();
        } else if (idModal === 'modal-registro') {
            const regForm = document.getElementById('formulario-registro');
            if (regForm) regForm.reset();
        }
    }
}

function cerrarModal(idModal) {
    const modal = document.getElementById(idModal);
    if (modal) {
        modal.classList.remove('activo');
        document.body.style.overflow = 'auto'; // Restablece scroll
    }
}

// Pasa de un modal a otro directamente (útil para ir de login a registro)
function cambiarModal(modalActual, modalSiguiente) {
    cerrarModal(modalActual);
    setTimeout(() => {
        abrirModal(modalSiguiente);
    }, 300); // Pequeño delay para que la transición visual se vea fluida
}


// =====================================================================
// 3. CARGA DE DATOS DE CATÁLOGO (HABITACIONES Y SERVICIOS)
// =====================================================================

// Obtener habitaciones desde la API
async function cargarHabitaciones(llegada = '', salida = '', totalPersonas = 0) {
    const contenedor = document.getElementById('habitaciones-contenedor');
    if (!contenedor) return;
    
    let url = '/api/habitaciones-disponibles';
    if (llegada && salida) {
        url += `?llegada=${llegada}&salida=${salida}`;
    }
    
    try {
        const respuesta = await fetch(url);
        const habitaciones = await respuesta.json();
        
        if (!respuesta.ok) {
            contenedor.innerHTML = `<p class="alerta alerta-advertencia">Error al cargar disponibilidad.</p>`;
            return;
        }
        
        catalogoHabitaciones = habitaciones; // Guardamos en memoria global
        
        if (habitaciones.length === 0) {
            contenedor.innerHTML = `<p class="alerta alerta-advertencia">Lo sentimos, no hay habitaciones libres para las fechas seleccionadas.</p>`;
            return;
        }
        
        // Mapeo de fotos locales de las habitaciones
        const fotosMapeo = {
            'Habitación Doble': 'imagenes/doble.png',
            'Suite Deluxe': 'imagenes/deluxe.png',
            'Habitación Familiar': 'imagenes/familiar.png',
            'Suite Frente al Mar': 'imagenes/playa_suite.png',
            'Habitación Sencilla': 'imagenes/sencilla.png',
            'Suite Presidencial Extra Lujo': 'imagenes/presidencial.png',
            'Villa Vista al Mar': 'imagenes/villa.png',
            'Habitación Individual Ejecutiva': 'imagenes/ejecutiva.png',
            'Penthouse Vista al Cielo': 'imagenes/penthouse.png'
        };
        
        let totalHabitacionesRenderizadas = 0;
        contenedor.innerHTML = ''; // Limpiar spinner
        
        habitaciones.forEach(hab => {
            // Filtrar por capacidad total si se especificó en la búsqueda
            if (totalPersonas > 0 && hab.Capacidad_Maxima < totalPersonas) {
                return;
            }
            totalHabitacionesRenderizadas++;
            
            const foto = fotosMapeo[hab.Nombre_Tipo] || 'imagenes/doble.png';
            
            // Si la consulta vino con fechas, hab tendrá el conteo de físicas libres.
            // Si no, mostramos capacidad genérica.
            const totalDispoTexto = hab.Habitaciones_Disponibles !== undefined 
                ? `<span class="badge-dispo"><i class="fa-solid fa-check"></i> ${hab.Habitaciones_Disponibles} disponibles</span>`
                : '';
                
            const precioMxn = parseFloat(hab.Precio_Noche) * TIPO_CAMBIO;
            const tarjetaHtml = `
                <div class="tarjeta-habitacion">
                    <div class="habitacion-img-contenedor">
                        <img src="${foto}" alt="${hab.Nombre_Tipo}">
                        <div class="precio-tag">$${precioMxn.toLocaleString('es-MX')} <span>MXN / Noche</span></div>
                    </div>
                    <div class="habitacion-detalles">
                        <h3>${hab.Nombre_Tipo}</h3>
                        <p>${hab.Descripcion}</p>
                        
                        <div class="habitacion-info-adicional">
                            <span><i class="fa-solid fa-users"></i> Capacidad Máx: ${hab.Capacidad_Maxima} personas</span>
                            ${totalDispoTexto}
                        </div>
                        
                        <button class="btn btn-primario" onclick="intentarReservar(${hab.ID_Tipo_Habitacion})">
                            <i class="fa-regular fa-calendar-check"></i> Reservar Habitación
                        </button>
                    </div>
                </div>
            `;
            contenedor.innerHTML += tarjetaHtml;
        });
        
        if (totalHabitacionesRenderizadas === 0) {
            contenedor.innerHTML = `<p class="alerta alerta-advertencia">Lo sentimos, no hay habitaciones libres con capacidad para ${totalPersonas} personas en las fechas seleccionadas.</p>`;
        }
        
    } catch (error) {
        console.error('Error al cargar habitaciones:', error);
        contenedor.innerHTML = `<p class="alerta alerta-advertencia">Error de conexión con el servidor.</p>`;
    }
}

// Carga los servicios en la sección del catálogo
async function cargarServicios() {
    const contenedor = document.getElementById('servicios-contenedor');
    if (!contenedor) return;
    
    try {
        const respuesta = await fetch('/api/servicios');
        const servicios = await respuesta.json();
        
        if (!respuesta.ok) {
            contenedor.innerHTML = `<p>Error al cargar servicios.</p>`;
            return;
        }
        
        catalogoServicios = servicios; // Guardar en global
        contenedor.innerHTML = ''; // Limpiar
        
        // Mapeo de iconos para que se vea genial
        const iconosMapeo = {
            'Piscina de Borde Infinito': 'fa-solid fa-water',
            'Spa & Wellness Center': 'fa-solid fa-spa',
            'Restaurante Gourmet Riviera': 'fa-solid fa-utensils',
            'Wi-Fi de Alta Velocidad': 'fa-solid fa-wifi',
            'Desayuno Buffet Premium': 'fa-solid fa-egg',
            'Tour de Avistamiento de Ballenas': 'fa-solid fa-ship',
            'Clase de Surf Privada': 'fa-solid fa-person-swimming',
            'Cena Romántica en la Playa': 'fa-solid fa-champagne-glasses'
        };
        
        servicios.forEach(serv => {
            const icono = iconosMapeo[serv.Nombre_Servicio] || 'fa-solid fa-bell';
            const precioMxn = parseFloat(serv.Precio) * TIPO_CAMBIO;
            const precioTexto = serv.Precio > 0 
                ? `$${precioMxn.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN` 
                : '¡Gratis!';
            
            const html = `
                <div class="tarjeta-servicio">
                    <div class="servicio-icono-caja">
                        <i class="${icono}"></i>
                    </div>
                    <h3>${serv.Nombre_Servicio}</h3>
                    <p>${serv.Descripcion_Corta}</p>
                    <span class="servicio-precio">${precioTexto}</span>
                </div>
            `;
            contenedor.innerHTML += html;
        });
        
    } catch (error) {
        console.error('Error al cargar servicios:', error);
    }
}


// =====================================================================
// 4. BÚSQUEDA Y FILTRADO POR FECHAS
// =====================================================================

function buscarDisponibilidad(event) {
    event.preventDefault();
    
    const llegada = document.getElementById('buscar-llegada').value;
    const salida = document.getElementById('buscar-salida').value;
    const adultos = parseInt(document.getElementById('buscar-adultos').value) || 0;
    const ninos = parseInt(document.getElementById('buscar-ninos').value) || 0;
    const totalPersonas = adultos + ninos;
    
    if (!llegada || !salida) {
        alert('Por favor selecciona las fechas de llegada y salida.');
        return;
    }
    
    if (new Date(salida) <= new Date(llegada)) {
        alert('La fecha de salida debe ser posterior a la fecha de llegada.');
        return;
    }
    
    // Mostramos la alerta de filtro activo
    const avisoFiltro = document.getElementById('filtro-fechas-aviso');
    const periodoTexto = document.getElementById('periodo-texto');
    
    periodoTexto.textContent = `${llegada} al ${salida} (Capacidad: ${totalPersonas} pers.)`;
    avisoFiltro.classList.remove('oculto');
    
    // Cargamos habitaciones filtradas
    cargarHabitaciones(llegada, salida, totalPersonas);

    // Desplazamos suavemente a la sección de habitaciones
    const seccionHabitaciones = document.getElementById('habitaciones');
    if (seccionHabitaciones) {
        seccionHabitaciones.scrollIntoView({ behavior: 'smooth' });
    }
}

// Botón de restablecer
function restablecerHabitaciones() {
    const avisoFiltro = document.getElementById('filtro-fechas-aviso');
    avisoFiltro.classList.add('oculto');
    
    // Resetear formulario
    const hoy = obtenerFechaFormateada(0);
    const mañana = obtenerFechaFormateada(1);
    document.getElementById('buscar-llegada').value = hoy;
    document.getElementById('buscar-salida').value = mañana;
    document.getElementById('buscar-adultos').value = "2";
    document.getElementById('buscar-ninos').value = "0";
    
    cargarHabitaciones();
}


// =====================================================================
// 5. FLUJO DE RESERVACIONES (MODAL DE DETALLES Y CÁLCULO INTERACTIVO)
// =====================================================================

// Se ejecuta al dar clic en "Reservar" en cualquier tarjeta
function intentarReservar(idTipoHabitacion) {
    // 1. Validar que el usuario esté logueado
    if (!usuarioLogueado) {
        alert('Para poder reservar una habitación, primero debes iniciar sesión.');
        abrirModal('modal-login');
        return;
    }
    
    // Buscar la habitación en nuestro catálogo en memoria
    habitacionSeleccionada = catalogoHabitaciones.find(h => h.ID_Tipo_Habitacion === idTipoHabitacion);
    if (!habitacionSeleccionada) return;
    
    // 2. Prefiliar información del modal
    document.getElementById('reserva-room-name').textContent = habitacionSeleccionada.Nombre_Tipo;
    document.getElementById('reserva-room-desc').textContent = habitacionSeleccionada.Descripcion;
    document.getElementById('reserva-room-cap').textContent = habitacionSeleccionada.Capacidad_Maxima;
    const precioRoomMxn = parseFloat(habitacionSeleccionada.Precio_Noche) * TIPO_CAMBIO;
    document.getElementById('reserva-room-price').textContent = `$${precioRoomMxn.toLocaleString('es-MX')} MXN`;
    
    // Mapeo de foto del modal
    const fotosMapeo = {
        'Habitación Doble': 'imagenes/doble.png',
        'Suite Deluxe': 'imagenes/deluxe.png',
        'Habitación Familiar': 'imagenes/familiar.png',
        'Suite Frente al Mar': 'imagenes/playa_suite.png',
        'Habitación Sencilla': 'imagenes/sencilla.png',
        'Suite Presidencial Extra Lujo': 'imagenes/presidencial.png',
        'Villa Vista al Mar': 'imagenes/villa.png',
        'Habitación Individual Ejecutiva': 'imagenes/ejecutiva.png',
        'Penthouse Vista al Cielo': 'imagenes/penthouse.png'
    };
    document.getElementById('reserva-room-img').src = fotosMapeo[habitacionSeleccionada.Nombre_Tipo] || 'imagenes/doble.png';
    
    // Prefiliar datos del huésped (Bloqueados)
    document.getElementById('res-form-nombre').value = `${usuarioLogueado.nombre} ${usuarioLogueado.apellido}`;
    document.getElementById('res-form-email').value = usuarioLogueado.email;
    document.getElementById('res-form-telefono').value = usuarioLogueado.telefono || 'Sin registrar';
    
    // Tomar las fechas del buscador principal si es que ya buscó por fecha
    const fechaLlegadaBusq = document.getElementById('buscar-llegada').value;
    const fechaSalidaBusq = document.getElementById('buscar-salida').value;
    
    const inputLlegadaForm = document.getElementById('res-form-llegada');
    const inputSalidaForm = document.getElementById('res-form-salida');
    
    // Fecha mínima es hoy
    const hoy = obtenerFechaFormateada(0);
    inputLlegadaForm.min = hoy;
    inputSalidaForm.min = obtenerFechaFormateada(1);
    
    inputLlegadaForm.value = fechaLlegadaBusq || hoy;
    inputSalidaForm.value = fechaSalidaBusq || obtenerFechaFormateada(1);
    
    // Poner adultos y niños del buscador
    document.getElementById('res-form-adultos').value = document.getElementById('buscar-adultos').value;
    document.getElementById('res-form-ninos').value = document.getElementById('buscar-ninos').value;
    
    // 3. Cargar la lista de servicios adicionales en formato Checklist
    cargarChecklistServicios();
    
    // 4. Calcular precios iniciales
    calcularPrecioTotal();
    validarCapacidadExcedida();
    
    // 5. Abrir el modal
    abrirModal('modal-reserva');
}

// Carga dinámicamente los servicios como checkboxes en el modal de reservas
function cargarChecklistServicios() {
    const contenedor = document.getElementById('checklist-servicios');
    if (!contenedor) return;
    
    contenedor.innerHTML = '';
    
    catalogoServicios.forEach(serv => {
        // Los servicios que cuestan 0 dólares ya están incluidos, no se cobran extra.
        // Pero los mostramos para que el cliente lo sepa.
        const esGratis = parseFloat(serv.Precio) === 0;
        const precioMxn = parseFloat(serv.Precio) * TIPO_CAMBIO;
        const textoPrecio = esGratis ? 'Incluido' : `+$${precioMxn.toLocaleString('es-MX')} MXN`;
        const checkedAtrib = esGratis ? 'checked disabled' : ''; // los gratis se auto-seleccionan y bloquean
        
        const html = `
            <div class="checklist-item">
                <label>
                    <input type="checkbox" name="servicio_reserva" value="${serv.ID_Servicio}" data-precio="${serv.Precio}" ${checkedAtrib} onchange="calcularPrecioTotal()">
                    <span>${serv.Nombre_Servicio}</span>
                </label>
                <span class="checklist-precio">${textoPrecio}</span>
            </div>
        `;
        contenedor.innerHTML += html;
    });
}

// Valida si el número de huéspedes excede el límite permitido
function validarCapacidadExcedida() {
    const adultos = parseInt(document.getElementById('res-form-adultos').value) || 0;
    const ninos = parseInt(document.getElementById('res-form-ninos').value) || 0;
    const totalPersonas = adultos + ninos;
    
    const alerta = document.getElementById('alerta-capacidad-reserva');
    const btnConfirmar = document.getElementById('btn-confirmar-reserva');
    
    if (habitacionSeleccionada && totalPersonas > habitacionSeleccionada.Capacidad_Maxima) {
        alerta.classList.remove('oculto');
        btnConfirmar.disabled = true;
        btnConfirmar.style.opacity = '0.5';
        btnConfirmar.style.cursor = 'not-allowed';
    } else {
        alerta.classList.add('oculto');
        btnConfirmar.disabled = false;
        btnConfirmar.style.opacity = '1';
        btnConfirmar.style.cursor = 'pointer';
    }
}

// Calcula el precio total de manera interactiva mientras el usuario cambia opciones (Como en la imagen)
function calcularPrecioTotal() {
    if (!habitacionSeleccionada) return;
    
    const fechaLlegada = document.getElementById('res-form-llegada').value;
    const fechaSalida = document.getElementById('res-form-salida').value;
    
    // Si no hay fechas correctas, salimos
    if (!fechaLlegada || !fechaSalida) return;
    
    const fLlegada = new Date(fechaLlegada);
    const fSalida = new Date(fechaSalida);
    
    // Calculamos la diferencia en milisegundos y la pasamos a días (noches)
    const diferenciaMs = fSalida.getTime() - fLlegada.getTime();
    let noches = Math.ceil(diferenciaMs / (1000 * 60 * 60 * 24));
    
    if (noches <= 0) noches = 0; // Evitar números negativos
    
    const precioNoche = parseFloat(habitacionSeleccionada.Precio_Noche);
    const subtotalHospedaje = precioNoche * noches;
    
    // Sumamos los servicios seleccionados (Los cobramos una sola vez para simplificar)
    let totalServicios = 0;
    const checkboxes = document.getElementsByName('servicio_reserva');
    checkboxes.forEach(cb => {
        if (cb.checked) {
            totalServicios += parseFloat(cb.getAttribute('data-precio') || 0);
        }
    });
    
    const granTotal = subtotalHospedaje + totalServicios;
    
    // Actualizamos los campos en la vista HTML (multiplicamos por un tipo de cambio de $20.00 MXN para dar valor local)
    // TIPO_CAMBIO global utilizado
    
    const precioNocheMxn = precioNoche * TIPO_CAMBIO;
    const subtotalHospedajeMxn = subtotalHospedaje * TIPO_CAMBIO;
    const totalServiciosMxn = totalServicios * TIPO_CAMBIO;
    const totalFinalMxn = granTotal * TIPO_CAMBIO;
    
    document.getElementById('res-calc-por-noche').textContent = `$${precioNocheMxn.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
    document.getElementById('res-calc-noches').textContent = `${noches} noche(s)`;
    document.getElementById('res-calc-hospedaje-total').textContent = `$${subtotalHospedajeMxn.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
    document.getElementById('res-calc-servicios-total').textContent = `$${totalServiciosMxn.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
    document.getElementById('res-calc-total-final').textContent = `$${totalFinalMxn.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
}

// Envía la confirmación de la reserva al backend
// Paso 1 al Paso 2: Ir a la pasarela de pago con tarjeta
function irAPasoPago(event) {
    event.preventDefault();
    
    // Cambiar visualmente de paso
    document.getElementById('reserva-paso-1').classList.add('oculto');
    document.getElementById('reserva-paso-2').classList.remove('oculto');
    document.getElementById('titulo-paso-reserva').innerHTML = `<i class="fa-solid fa-credit-card"></i> Pago de Reservación`;
    
    // Auto-completar el titular de la tarjeta con el nombre del usuario
    const inputNombre = document.getElementById('card-nombre');
    if (inputNombre && !inputNombre.value && usuarioLogueado) {
        inputNombre.value = `${usuarioLogueado.nombre} ${usuarioLogueado.apellido}`.toUpperCase();
    }
    
    actualizarTarjetaVirtual();
}

// Regresar del Paso 2 al Paso 1
function regresarAPaso1() {
    document.getElementById('reserva-paso-2').classList.add('oculto');
    document.getElementById('reserva-paso-1').classList.remove('oculto');
    document.getElementById('titulo-paso-reserva').innerHTML = `<i class="fa-regular fa-address-card"></i> Detalles de la Reserva`;
}

// Actualiza dinámicamente la tarjeta de crédito de juguete en la pantalla
function actualizarTarjetaVirtual() {
    const numInput = document.getElementById('card-numero');
    const nomInput = document.getElementById('card-nombre');
    const expInput = document.getElementById('card-exp');
    
    const vistaNum = document.getElementById('vista-tarjeta-numero');
    const vistaNom = document.getElementById('vista-tarjeta-nombre');
    const vistaExp = document.getElementById('vista-tarjeta-exp');
    const logoTipo = document.getElementById('tarjeta-logo-tipo');
    
    // 1. Darle formato de 4 en 4 dígitos al número de tarjeta en el input
    let numVal = numInput.value.replace(/\D/g, ''); // Quitamos todo lo que no sea número
    let numFormateado = [];
    for (let i = 0; i < numVal.length; i += 4) {
        numFormateado.push(numVal.substring(i, i + 4));
    }
    numInput.value = numFormateado.join(' ');
    
    // Actualizar vista
    vistaNum.textContent = numInput.value || '•••• •••• •••• ••••';
    
    // Detectar Tipo de Tarjeta (Visa empieza con 4, Mastercard con 5)
    if (numVal.startsWith('4')) {
        logoTipo.className = 'fa-brands fa-cc-visa logo-tarjeta-tipo';
    } else if (numVal.startsWith('5')) {
        logoTipo.className = 'fa-brands fa-cc-mastercard logo-tarjeta-tipo';
    } else {
        logoTipo.className = 'fa-solid fa-credit-card logo-tarjeta-tipo';
    }
    
    // 2. Nombre del titular
    vistaNom.textContent = nomInput.value.toUpperCase() || 'NOMBRE COMPLETO';
    
    // 3. Fecha de expiración (dar formato MM/AA)
    let expVal = expInput.value.replace(/\D/g, '');
    if (expVal.length > 2) {
        expInput.value = expVal.substring(0, 2) + '/' + expVal.substring(2, 4);
    } else {
        expInput.value = expVal;
    }
    vistaExp.textContent = expInput.value || 'MM/AA';
}

// Paso 2 al Paso 4: Simular cobro bancario y registrar en MySQL
async function procesarPago(event) {
    event.preventDefault();
    
    if (!usuarioLogueado || !habitacionSeleccionada) return;
    
    // Cambiar al Paso 3: Cargando / validando
    document.getElementById('reserva-paso-2').classList.add('oculto');
    document.getElementById('reserva-paso-3').classList.remove('oculto');
    document.getElementById('titulo-paso-reserva').innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Validando...`;
    
    // Obtenemos los campos de la reserva del Paso 1
    const fecha_llegada = document.getElementById('res-form-llegada').value;
    const fecha_salida = document.getElementById('res-form-salida').value;
    const adultos = parseInt(document.getElementById('res-form-adultos').value);
    const ninos = parseInt(document.getElementById('res-form-ninos').value) || 0;
    
    // Servicios adicionales seleccionados
    const serviciosSeleccionados = [];
    const checkboxes = document.getElementsByName('servicio_reserva');
    checkboxes.forEach(cb => {
        if (cb.checked) {
            serviciosSeleccionados.push({
                id_servicio: parseInt(cb.value),
                cantidad: 1
            });
        }
    });
    
    // Datos de la tarjeta del Paso 2
    const tarjeta_nombre = document.getElementById('card-nombre').value;
    const tarjeta_numero = document.getElementById('card-numero').value;
    
    const cuerpoReserva = {
        id_huesped: usuarioLogueado.id,
        id_tipo_habitacion: habitacionSeleccionada.ID_Tipo_Habitacion,
        fecha_llegada,
        fecha_salida,
        adultos,
        ninos,
        servicios: serviciosSeleccionados,
        tarjeta_nombre,
        tarjeta_numero
    };
    
    // Simular un retardo del servidor de pago de 2 segundos para dar realismo interactivo
    setTimeout(async () => {
        try {
            const respuesta = await fetch('/api/reservar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cuerpoReserva)
            });
            
            const datos = await respuesta.json();
            
            // Si el servidor de Flask responde error (ej. sin disponibilidad)
            if (!respuesta.ok) {
                alert(datos.error || 'La transacción ha sido rechazada por el servidor.');
                // Regresar al paso 2
                document.getElementById('reserva-paso-3').classList.add('oculto');
                document.getElementById('reserva-paso-2').classList.remove('oculto');
                document.getElementById('titulo-paso-reserva').innerHTML = `<i class="fa-solid fa-credit-card"></i> Pago de Reservación`;
                return;
            }
            
            // Ocultamos cargador
            document.getElementById('reserva-paso-3').classList.add('oculto');
            
            // --- CONSTRUIR TICKET DIGITAL (PASO 4) ---
            document.getElementById('reserva-paso-4').classList.remove('oculto');
            document.getElementById('titulo-paso-reserva').innerHTML = `<i class="fa-solid fa-square-check" style="color:var(--verde-confirmar);"></i> ¡Reserva Confirmada!`;
            
            // Folio e Información General
            document.getElementById('ticket-folio').textContent = `#${datos.id_reserva}`;
            document.getElementById('ticket-fecha-emision').textContent = new Date().toLocaleDateString('es-MX', {
                year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
            });
            document.getElementById('ticket-nombre-cliente').textContent = `${usuarioLogueado.nombre} ${usuarioLogueado.apellido}`;
            document.getElementById('ticket-email-cliente').textContent = usuarioLogueado.email;
            document.getElementById('ticket-tipo-hab').textContent = habitacionSeleccionada.Nombre_Tipo;
            
            // Asignar número de habitación (Flask regresa ID, estimamos un número físico para el ticket)
            const numHabMapeo = { 1: '101', 2: '201', 3: '301', 4: '401' };
            document.getElementById('ticket-num-hab').textContent = numHabMapeo[habitacionSeleccionada.ID_Tipo_Habitacion] || '102';
            
            document.getElementById('ticket-checkin').textContent = fecha_llegada;
            document.getElementById('ticket-checkout').textContent = fecha_salida;
            document.getElementById('ticket-huespedes').textContent = `${adultos} Adulto(s), ${ninos} Niño(s)`;
            
            // Cargar los servicios en el ticket
            const ulServicios = document.getElementById('ticket-servicios-adicionales');
            ulServicios.innerHTML = '';
            
            let costoServiciosTotal = 0;
            let algunServicio = false;
            
            checkboxes.forEach(cb => {
                if (cb.checked) {
                    algunServicio = true;
                    const nombre = cb.nextElementSibling.textContent;
                    const precio = parseFloat(cb.getAttribute('data-precio') || 0);
                    costoServiciosTotal += precio;
                    const precioMxn = precio * TIPO_CAMBIO;
                    const precioText = precio === 0 ? 'Incluido' : `$${precioMxn.toLocaleString('es-MX', { minimumFractionDigits: 2 })} MXN`;
                    ulServicios.innerHTML += `<li><span>${nombre}</span> <strong>${precioText}</strong></li>`;
                }
            });
            
            if (!algunServicio) {
                ulServicios.innerHTML = '<li><em>Ninguno</em></li>';
            }
            
            // Calcular costos totales para el ticket
            const fLlegada = new Date(fecha_llegada);
            const fSalida = new Date(fecha_salida);
            const noches = Math.ceil((fSalida - fLlegada) / (1000 * 60 * 60 * 24)) || 1;
            const subtotalHosp = parseFloat(habitacionSeleccionada.Precio_Noche) * noches;
            const granTotalUsd = subtotalHosp + costoServiciosTotal;
            // TIPO_CAMBIO global utilizado
            const granTotalMxn = granTotalUsd * TIPO_CAMBIO;
            
            const subtotalHospMxn = subtotalHosp * TIPO_CAMBIO;
            const costoServiciosTotalMxn = costoServiciosTotal * TIPO_CAMBIO;
            
            document.getElementById('ticket-subtotal-hosp').textContent = `$${subtotalHospMxn.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
            document.getElementById('ticket-subtotal-serv').textContent = `$${costoServiciosTotalMxn.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
            document.getElementById('ticket-total-pagado').textContent = `$${granTotalMxn.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
            
            // Desactivar el botón X de cerrar del modal para forzar al usuario a hacer clic en "Finalizar"
            const botonCerrar = document.querySelector('#modal-reserva .cerrar-modal-btn');
            if (botonCerrar) botonCerrar.style.display = 'none';
            
        } catch (error) {
            console.error('Error al procesar reserva y pago:', error);
            alert('Falla al conectar al servidor de pagos.');
            // Regresar al paso 2
            document.getElementById('reserva-paso-3').classList.add('oculto');
            document.getElementById('reserva-paso-2').classList.remove('oculto');
            document.getElementById('titulo-paso-reserva').innerHTML = `<i class="fa-solid fa-credit-card"></i> Pago de Reservación`;
        }
    }, 2000); // 2 segundos de loading de banco
}

// Imprimir el ticket de reservación usando el CSS media print del navegador
function imprimirTicket() {
    window.print();
}

// Finaliza todo el flujo del modal y regresa al estado original
function cerrarFlujoReservaCompleto() {
    // Reactivar botón X
    const botonCerrar = document.querySelector('#modal-reserva .cerrar-modal-btn');
    if (botonCerrar) botonCerrar.style.display = 'block';
    
    // Cerrar modal
    cerrarModal('modal-reserva');
    
    // Esperar a que cierre y restablecer el wizard al Paso 1
    setTimeout(() => {
        document.getElementById('reserva-paso-4').classList.add('oculto');
        document.getElementById('reserva-paso-1').classList.remove('oculto');
        document.getElementById('titulo-paso-reserva').innerHTML = `<i class="fa-regular fa-address-card"></i> Detalles de la Reserva`;
        
        // Resetear inputs de tarjeta
        document.getElementById('card-nombre').value = '';
        document.getElementById('card-numero').value = '';
        document.getElementById('card-exp').value = '';
        document.getElementById('card-cvv').value = '';
        
        // Limpiar habitaciones
        restablecerHabitaciones();
    }, 500);
}


// =====================================================================
// 6. PANEL DE USUARIO (VER HISTORIAL DE RESERVAS Y CANCELAR)
// =====================================================================

function abrirPanelUsuario() {
    if (!usuarioLogueado) return;
    
    // Configurar el perfil del usuario en el modal
    document.getElementById('perfil-nombre-completo').textContent = `${usuarioLogueado.nombre} ${usuarioLogueado.apellido}`;
    document.getElementById('perfil-email').textContent = usuarioLogueado.email;
    
    // Cargar sus reservas
    cargarHistorialReservas();
    
    abrirModal('modal-panel-usuario');
}

// Carga las reservas del usuario del backend y las renderiza
async function cargarHistorialReservas() {
    const contenedor = document.getElementById('lista-reservas-contenedor');
    if (!contenedor) return;
    
    try {
        const respuesta = await fetch(`/api/mis-reservas?id_huesped=${usuarioLogueado.id}`);
        const reservas = await respuesta.json();
        
        if (!respuesta.ok) {
            contenedor.innerHTML = `<p class="alerta alerta-advertencia">Error al cargar reservas.</p>`;
            return;
        }
        
        if (reservas.length === 0) {
            contenedor.innerHTML = `<p style="text-align:center; padding: 20px; color: #777;">No tienes ninguna reserva registrada actualmente.</p>`;
            return;
        }
        
        contenedor.innerHTML = ''; // Limpiar spinner
        
        // TIPO_CAMBIO global utilizado
        
        reservas.forEach(res => {
            // Formatear fechas
            const llegadaFormateada = res.Fecha_Llegada.split('T')[0];
            const salidaFormateada = res.Fecha_Salida.split('T')[0];
            
            // Determinar si la reserva ya concluyó en la fecha actual
            const fechaSalidaDate = new Date(salidaFormateada);
            const hoyDate = new Date();
            fechaSalidaDate.setHours(0,0,0,0);
            hoyDate.setHours(0,0,0,0);
            
            let estadoReserva = res.Estado_Reserva;
            if (estadoReserva !== 'Cancelada' && fechaSalidaDate < hoyDate) {
                estadoReserva = 'Finalizada';
            }

            // Badge del estado
            let badgeClase = 'badge-pendiente';
            let estadoTexto = estadoReserva;
            if (estadoReserva === 'Confirmada') badgeClase = 'badge-confirmada';
            if (estadoReserva === 'Cancelada') badgeClase = 'badge-cancelada';
            if (estadoReserva === 'Finalizada') {
                badgeClase = 'badge-finalizada';
                estadoTexto = 'Finalizada (Ya fue)';
            }
            
            // Listar los servicios contratados
            let serviciosHtml = '<li><em>Ningún servicio extra contratado</em></li>';
            if (res.ServiciosAdicionales && res.ServiciosAdicionales.length > 0) {
                serviciosHtml = '';
                res.ServiciosAdicionales.forEach(s => {
                    const precioS_Mxn = parseFloat(s.Precio) * TIPO_CAMBIO;
                    const precioS = parseFloat(s.Precio) === 0 ? 'Incluido' : `$${precioS_Mxn.toLocaleString('es-MX')} MXN`;
                    serviciosHtml += `<li><span>${s.Nombre_Servicio}</span> <strong>${precioS}</strong></li>`;
                });
            }
            
            // Botón de cancelar (Solo visible para reservas activas y no vencidas)
            const esCancelable = estadoReserva === 'Confirmada' || estadoReserva === 'Pendiente';
            const botonCancelarHtml = esCancelable
                ? `<button class="btn btn-rojo" style="padding: 6px 12px; font-size: 0.8rem;" onclick="cancelarReservaCliente(${res.ID_Reserva})">
                     <i class="fa-solid fa-ban"></i> Cancelar Reserva
                   </button>`
                : '';
            
            const totalPesos = parseFloat(res.Costo_Total) * TIPO_CAMBIO;
            
            const html = `
                <div class="item-reserva">
                    <div class="reserva-cabecera">
                        <div>
                            <span class="reserva-id">Reserva #${res.ID_Reserva}</span>
                            <span style="color: #888; font-size:0.8rem; margin-left: 10px;">Creado: ${res.Fecha_Creacion.split('T')[0]}</span>
                        </div>
                        <span class="reserva-estado-badge ${badgeClase}">${estadoTexto}</span>
                    </div>
                    
                    <div class="reserva-content-grid reserva-contenido">
                        <div class="reserva-detalles-texto">
                            <p><strong>Habitación:</strong> ${res.Nombre_Tipo} (Hab. ${res.Numero_Habitacion})</p>
                            <p><i class="fa-regular fa-calendar"></i> Entrada: ${llegadaFormateada}</p>
                            <p><i class="fa-regular fa-calendar"></i> Salida: ${salidaFormateada}</p>
                            <p><i class="fa-solid fa-users"></i> Huéspedes: ${res.Numero_Adultos} Adultos, ${res.Numero_Ninos} Niños</p>
                        </div>
                        
                        <div class="reserva-servicios-listados">
                            <h5>Servicios Extras:</h5>
                            <ul>
                                ${serviciosHtml}
                            </ul>
                        </div>
                    </div>
                    
                    <div class="reserva-acciones">
                        <span class="reserva-total-pago">Total: $${totalPesos.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN</span>
                        ${botonCancelarHtml}
                    </div>
                </div>
            `;
            contenedor.innerHTML += html;
        });
        
    } catch (error) {
        console.error('Error al cargar historial:', error);
    }
}

// Cancela la reserva desde el panel del usuario
async function cancelarReservaCliente(idReserva) {
    if (!confirm('¿Realmente deseas cancelar esta reservación? Esta acción es definitiva.')) return;
    
    try {
        const respuesta = await fetch('/api/cancelar-reserva', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_reserva: idReserva, id_huesped: usuarioLogueado.id })
        });
        
        const datos = await respuesta.json();
        
        if (!respuesta.ok) {
            alert(datos.error || 'No se pudo cancelar la reserva.');
            return;
        }
        
        alert('¡Tu reserva ha sido cancelada correctamente!');
        
        // Recargar la lista de reservas
        cargarHistorialReservas();
        
        // Recargar habitaciones por si se liberaron espacios
        restablecerHabitaciones();
        
    } catch (error) {
        console.error('Error al cancelar:', error);
        alert('Ocurrió un error de red al intentar cancelar.');
    }
}


// =====================================================================
// 7. CARGA Y REGISTRO DE TESTIMONIOS
// =====================================================================

async function cargarTestimonios() {
    const lista = document.getElementById('testimonios-lista');
    if (!lista) return;
    
    try {
        const respuesta = await fetch('/api/testimonios');
        const testimonios = await respuesta.json();
        
        if (!respuesta.ok) {
            lista.innerHTML = `<p>Error al cargar testimonios.</p>`;
            return;
        }
        
        lista.innerHTML = '';
        
        if (testimonios.length === 0) {
            lista.innerHTML = `<p style="grid-column: 1/-1; text-align:center; color:#777;">Aún no hay testimonios aprobados. ¡Sé el primero en comentar!</p>`;
            return;
        }
        
        testimonios.forEach(t => {
            // Estrellas HTML
            let estrellasHtml = '';
            for (let i = 1; i <= 5; i++) {
                if (i <= t.Calificacion_Estrellas) {
                    estrellasHtml += '<i class="fa-solid fa-star"></i>';
                } else {
                    estrellasHtml += '<i class="fa-regular fa-star"></i>';
                }
            }
            
            // Imagen por defecto del usuario o la suya
            const fotoPerfil = t.URL_Foto_Perfil || 'https://www.w3schools.com/howto/img_avatar.png';
            
            const html = `
                <div class="tarjeta-testimonio">
                    <div class="testimonio-estrellas">${estrellasHtml}</div>
                    <p class="testimonio-comentario">"${t.Comentario}"</p>
                    <div class="testimonio-autor">
                        <img class="testimonio-foto" src="${fotoPerfil}" alt="${t.Nombre}">
                        <div class="autor-nombre">
                            <h4>${t.Nombre} ${t.Apellido}</h4>
                            <span>Huésped Registrado</span>
                        </div>
                    </div>
                </div>
            `;
            lista.innerHTML += html;
        });
        
    } catch (error) {
        console.error('Error al cargar testimonios:', error);
    }
}

// Envía un nuevo testimonio al backend
async function enviarTestimonio(event) {
    event.preventDefault();
    
    if (!usuarioLogueado) return;
    
    const comentario = document.getElementById('comentario-testimonio').value;
    
    // Obtener la calificacion de los radio buttons
    let calificacion = 5;
    const radios = document.getElementsByName('estrellas');
    for (const r of radios) {
        if (r.checked) {
            calificacion = parseInt(r.value);
            break;
        }
    }
    
    try {
        const respuesta = await fetch('/api/testimonios', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_huesped: usuarioLogueado.id,
                comentario,
                calificacion
            })
        });
        
        const datos = await respuesta.json();
        
        if (!respuesta.ok) {
            alert(datos.error || 'Error al guardar comentario.');
            return;
        }
        
        alert('¡Comentario publicado con éxito!');
        document.getElementById('comentario-testimonio').value = '';
        
        // Recargar testimonios
        cargarTestimonios();
        
    } catch (error) {
        console.error('Error al guardar testimonio:', error);
    }
}


// =====================================================================
// 8. SUSCRIPCIÓN AL BOLETÍN
// =====================================================================

async function suscribirBoletin(event) {
    event.preventDefault();
    
    const emailInput = document.getElementById('correo-boletin');
    const email = emailInput.value;
    
    try {
        const respuesta = await fetch('/api/suscribir', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        
        const datos = await respuesta.json();
        
        if (!respuesta.ok) {
            alert(datos.error || 'Error al suscribirse.');
            return;
        }
        
        alert(datos.mensaje || '¡Suscripción exitosa!');
        emailInput.value = '';
        
    } catch (error) {
        console.error('Error al suscribir:', error);
        alert('No se pudo procesar la suscripción.');
    }
}

const descripcionesGaleria = {
    'Fachada & Piscina': {
        desc: 'Nuestra icónica piscina de borde infinito climatizada a 28°C se funde con el horizonte del Océano Pacífico. Un espacio exclusivo diseñado para relajarse en camastros flotantes y disfrutar de la mejor coctelería tropical mientras contemplas los atardeceres legendarios de la Riviera.',
        badge1: '<i class="fa-solid fa-clock"></i> Horario: 8:00 AM - 10:00 PM',
        badge2: '<i class="fa-solid fa-glass-water"></i> Servicio de Pool Bar incluido'
    },
    'Nuestra Playa Privada': {
        desc: 'Una bahía de arenas blancas y aguas cálidas exclusivas para nuestros huéspedes. Perfecta para dar paseos matutinos, practicar paddle surf o simplemente descansar bajo la sombra de nuestras palapas con servicio de mesero personalizado.',
        badge1: '<i class="fa-solid fa-umbrella-beach"></i> Área de camastros exclusiva',
        badge2: '<i class="fa-solid fa-person-swimming"></i> Salvavidas y seguridad 24/7'
    },
    'Interiores Suite': {
        desc: 'Habitaciones diseñadas bajo un concepto de lujo descalzo: acabados de mármol, maderas finas locales y tecnología inteligente para automatizar luces y temperatura. Cada detalle está pensado para garantizar un descanso reparador frente al mar.',
        badge1: '<i class="fa-solid fa-wind"></i> Aire acondicionado inteligente',
        badge2: '<i class="fa-solid fa-bed"></i> Sábanas de algodón egipcio de 500 hilos'
    },
    'Cabinas de Spa': {
        desc: 'Un santuario de bienestar físico y mental. Ofrecemos masajes de tejido profundo, tratamientos faciales con ingredientes orgánicos locales y circuito de hidroterapia con sauna aromático para renovar tus energías por completo.',
        badge1: '<i class="fa-solid fa-spa"></i> Terapeutas certificados internacionales',
        badge2: '<i class="fa-solid fa-droplet"></i> Circuito de hidroterapia de vapor'
    },
    'Restaurante Riviera': {
        desc: 'Experiencia culinaria de primer nivel frente al mar. Nuestro menú a la carta ofrece platillos gourmet creados con pesca fresca del día y maridados con una selecta cava de vinos nacionales e internacionales.',
        badge1: '<i class="fa-solid fa-utensils"></i> Cena a la carta: 6:00 PM - 11:00 PM',
        badge2: '<i class="fa-solid fa-wine-glass"></i> Sommelier exclusivo disponible'
    },
    'Desayuno Premium': {
        desc: 'Comienza tu mañana con nuestro buffet frente a la playa. Estación de panadería artesanal horneada en casa, jugos naturales prensados al momento, frutas exóticas de temporada y barra caliente de especialidades mexicanas al gusto.',
        badge1: '<i class="fa-solid fa-mug-saucer"></i> Horario buffet: 7:00 AM - 11:30 AM',
        badge2: '<i class="fa-solid fa-wheat-awn"></i> Opciones sin gluten disponibles'
    }
};

function inicializarGaleriaLightbox() {
    const items = document.querySelectorAll('.foto-item');
    items.forEach(item => {
        item.style.cursor = 'pointer';
        item.addEventListener('click', () => {
            const img = item.querySelector('img');
            const title = item.querySelector('.foto-info h4');
            if (img && title) {
                abrirLightbox(img.src, title.textContent);
            }
        });
    });
}

function abrirLightbox(src, desc) {
    const overlay = document.getElementById('lightbox-galeria');
    const overlayImg = document.getElementById('lightbox-imagen');
    const overlayTitle = document.getElementById('lightbox-titulo');
    const overlayDesc = document.getElementById('lightbox-descripcion');
    const badge1 = document.getElementById('lightbox-badge-1');
    const badge2 = document.getElementById('lightbox-badge-2');
    
    if (overlay && overlayImg && overlayTitle) {
        overlayImg.src = src;
        overlayTitle.textContent = desc;
        
        // Cargar detalles específicos
        const detalles = descripcionesGaleria[desc.trim()];
        if (detalles) {
            if (overlayDesc) overlayDesc.textContent = detalles.desc;
            if (badge1) badge1.innerHTML = detalles.badge1;
            if (badge2) badge2.innerHTML = detalles.badge2;
        } else {
            if (overlayDesc) overlayDesc.textContent = 'Explora nuestras hermosas instalaciones en el Hotel Riviera.';
            if (badge1) badge1.innerHTML = '<i class="fa-solid fa-clock"></i> Acceso disponible';
            if (badge2) badge2.innerHTML = '<i class="fa-solid fa-bell"></i> Servicio exclusivo';
        }
        
        overlay.classList.add('activo');
        document.body.style.overflow = 'hidden'; // Evita scroll de fondo
    }
}

function cerrarLightbox() {
    const overlay = document.getElementById('lightbox-galeria');
    if (overlay) {
        overlay.classList.remove('activo');
        // Solo restaurar el body overflow si no hay otros modales abiertos
        const modalesActivos = document.querySelectorAll('.capa-modal.activo');
        if (modalesActivos.length === 0) {
            document.body.style.overflow = 'auto';
        }
    }
}
