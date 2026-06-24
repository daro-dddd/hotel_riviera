import urllib.request
import json

def make_request(url, data=None, method='GET'):
    req = urllib.request.Request(url, method=method)
    if data is not None:
        req.add_header('Content-Type', 'application/json')
        jsondata = json.dumps(data).encode('utf-8')
    else:
        jsondata = None
    
    try:
        with urllib.request.urlopen(req, data=jsondata) as response:
            res_data = response.read().decode('utf-8')
            return response.status, json.loads(res_data)
    except urllib.error.HTTPError as e:
        res_data = e.read().decode('utf-8')
        return e.code, json.loads(res_data)
    except Exception as e:
        return 0, str(e)

def run_tests():
    base_url = "http://127.0.0.1:5000"
    print("=== 1. Probando Inicio de Sesión de Administrador ===")
    credentials = {
        "email": "admin@hotelriviera.com",
        "contrasena": "admin123"
    }
    status, res = make_request(f"{base_url}/api/iniciar-sesion", credentials, 'POST')
    print(f"Status: {status}")
    print(f"Response: {res}")
    assert status == 200, "Error al iniciar sesión"
    assert res['usuario']['es_admin'] is True, "El usuario no es administrador"
    print("¡Inicio de sesión de administrador exitoso!\n")

    print("=== 2. Probando Cambio de Estado de Habitación a 'Reservada' ===")
    # Buscaremos la habitación con número 101 (suele ser ID 1)
    # Primero listamos las habitaciones para ver sus IDs y estados
    status, habitaciones = make_request(f"{base_url}/api/admin/habitaciones", method='GET')
    assert status == 200, "Error al obtener habitaciones"
    
    room_101 = next((h for h in habitaciones if h['Numero_Habitacion'] == '101'), None)
    assert room_101 is not None, "No se encontró la habitación 101"
    id_hab = room_101['ID_Habitacion']
    estado_original = room_101['Estado']
    print(f"Habitación 101 ID: {id_hab}, Estado actual: {estado_original}")

    # Cambiar a Reservada
    cambio = {
        "id_habitacion": id_hab,
        "estado": "Reservada"
    }
    status, res = make_request(f"{base_url}/api/admin/habitaciones/estado", cambio, 'POST')
    print(f"Actualizar a Reservada - Status: {status}, Response: {res}")
    assert status == 200, "Error al actualizar estado a Reservada"

    # Verificar que cambió
    status, habitaciones = make_request(f"{base_url}/api/admin/habitaciones", method='GET')
    room_101 = next((h for h in habitaciones if h['ID_Habitacion'] == id_hab), None)
    print(f"Nuevo estado en la base de datos: {room_101['Estado']}")
    assert room_101['Estado'] == 'Reservada', "El estado no se actualizó a Reservada"
    print("¡Cambio a 'Reservada' exitoso!\n")

    # Regresar a Disponible
    cambio['estado'] = 'Disponible'
    status, res = make_request(f"{base_url}/api/admin/habitaciones/estado", cambio, 'POST')
    print(f"Restablecer a Disponible - Status: {status}")
    assert status == 200

    print("=== 3. Probando flujo de Reservación Completo ===")
    # Vamos a crear una reservación para el huésped Carlos Martínez (ID 1 en base_de_datos.sql)
    # Buscaremos habitación física libre para Tipo de Habitación 1 (Habitación Doble)
    booking_data = {
        "id_huesped": 1,
        "id_tipo_habitacion": 1,
        "fecha_llegada": "2026-07-01",
        "fecha_salida": "2026-07-05",
        "adultos": 2,
        "ninos": 1,
        "tarjeta_nombre": "Carlos Martinez",
        "tarjeta_numero": "1234567812345678",
        "servicios": []
    }
    status, res = make_request(f"{base_url}/api/reservar", booking_data, 'POST')
    print(f"Reservar - Status: {status}, Response: {res}")
    assert status == 201, "Error al realizar la reserva"
    reserva_id = res['id_reserva']
    id_habitacion_reservada = res['id_habitacion']
    print(f"Reserva creada con ID: {reserva_id} en habitación ID: {id_habitacion_reservada}")

    # Verificar que el estado de la habitación física cambió a 'Reservada'
    status, habitaciones = make_request(f"{base_url}/api/admin/habitaciones", method='GET')
    room_res = next((h for h in habitaciones if h['ID_Habitacion'] == id_habitacion_reservada), None)
    print(f"Estado de la habitación reservada: {room_res['Estado']}")
    assert room_res['Estado'] == 'Reservada', "La habitación no cambió a Reservada tras la reserva"
    print("¡Sincronización de reserva a estado 'Reservada' exitosa!\n")

    print("=== 4. Probando cancelación de Reserva ===")
    cancel_data = {
        "id_reserva": reserva_id,
        "id_huesped": 1
    }
    status, res = make_request(f"{base_url}/api/cancelar-reserva", cancel_data, 'POST')
    print(f"Cancelar Reserva - Status: {status}, Response: {res}")
    assert status == 200, "Error al cancelar la reserva"

    # Verificar que el estado de la habitación física regresó a 'Disponible'
    status, habitaciones = make_request(f"{base_url}/api/admin/habitaciones", method='GET')
    room_res = next((h for h in habitaciones if h['ID_Habitacion'] == id_habitacion_reservada), None)
    print(f"Estado de la habitación tras cancelación: {room_res['Estado']}")
    assert room_res['Estado'] == 'Disponible', "La habitación no regresó a Disponible tras la cancelación"
    print("¡Sincronización de cancelación a estado 'Disponible' exitosa!\n")

    print("====================================================")
    print("   TODAS LAS PRUEBAS SE COMPLETARON CON ÉXITO")
    print("====================================================")

if __name__ == "__main__":
    run_tests()
