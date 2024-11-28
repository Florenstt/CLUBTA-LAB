import uasyncio as asyncio  # Reemplazar por `asyncio` si utiliza CircuitPython
# Reemplazar por `circuit_monitoring` si utiliza CircuitPython
import micro_monitoring
import machine
import time
import select
import sys

# Variable global para el nombre del color actual
current_color_name = "Apagado"
current_color = (0, 0, 0)  # Color inicial (apagado)
brightness_factor = 1.0
led_off = False
touch_count = 0
sensor_activated = False
intensity_reset = False

def get_app_data():
    # Función que devuelve un `dict` con la data para el maestro.
    return {"color": current_color_name}

async def serial_controls(colors, set_color):
    global current_color_name, current_color, brightness_factor, led_off, intensity_reset
    while True:
        if select.select([sys.stdin], [], [], 0)[0]:
            command = sys.stdin.readline().strip().lower()

            if command in colors:
                current_color = colors[command]
                current_color_name = command  # Actualizar el nombre del color actual
                brightness_factor = 1.0  # Restablecer el brillo a su valor máximo
                await set_color(*current_color, brightness_factor)
                led_off = False
                intensity_reset = False  # Resetear el estado de intensidad
                print(f"Color cambiado a: {command}")
            elif command == "off":
                await set_color(0, 0, 0)  # Apagar el LED
                led_off = True
                intensity_reset = False  # Resetear el estado de intensidad
                print("LED apagado.")
            elif command == "on" and led_off:
                await set_color(*current_color, brightness_factor)  # Encender LED con el color actual
                led_off = False

        if intensity_reset and (select.select([sys.stdin], [], [], 0)[0]):
            intensity_reset = False  # Permitir nuevos cambios de brillo después de recibir una instrucción

        await asyncio.sleep(0.1)  # Reducción del tiempo de espera para hacer la disminución más rápida

async def button_controls(colors, set_color, button_pin):
    global current_color_name, current_color, brightness_factor, touch_count, intensity_reset
    while True:
        if not button_pin.value():  # Botón presionado
            start_time = time.time()
            # Esperar 5 segundos para registrar más toques
            while time.time() - start_time < 5:
                if not button_pin.value():
                    touch_count += 1  # Sumar toques dentro de los 5 segundos
                    print(f"Toque detectado. Total de toques: {touch_count}")  # Mostrar cantidad de toques
                    time.sleep(0.2)  # De-bounce
                time.sleep(0.1)

            # Seleccionar color basado en la cantidad de toques dentro de 5 segundos
            if touch_count == 1:
                current_color = colors["blanco"]
            elif touch_count == 2:
                current_color = colors["rojo"]
            elif touch_count == 3:
                current_color = colors["morado"]
            elif touch_count == 4:
                current_color = colors["amarillo"]
            elif touch_count == 5:
                current_color = colors["rosado"]
            elif touch_count == 6:
                current_color = colors["verde"]
            elif touch_count >= 7:
                # Efecto multicolor para 7 o más toques
                for color in colors.values():
                    await set_color(*color, brightness_factor)
                    time.sleep(1)
                await set_color(0, 0, 0)  # Apagar el LED al final del efecto multicolor
                print("Efecto multicolor completado.")
                touch_count = 0  # Resetear contador de toques
                continue  # No cambiar el color directamente después del efecto

            # Aplicar el color seleccionado
            brightness_factor = 1.0  # Restablecer el brillo a su valor máximo
            await set_color(*current_color, brightness_factor)
            current_color_name = list(colors.keys())[list(colors.values()).index(current_color)]  # Actualizar el nombre del color actual
            print(f"Color cambiado por botón: {current_color_name}")
            touch_count = 0  # Resetear contador de toques
            intensity_reset = False  # Resetear el estado de intensidad
            time.sleep(0.2)  # De-bounce

        await asyncio.sleep(0.1)

async def sensor_controls(sensor_pin, set_color):
    global current_color, brightness_factor, led_off, intensity_reset
    while True:
        # Detectar activación del sensor
        if not sensor_pin.value() and not led_off and not intensity_reset:  # Sensor activado y no reseteado
            if brightness_factor > 0.1:
                # Disminuir el brillo en pasos de 0.05 para que sea más rápido pero aún suave
                brightness_factor -= 0.05
                await set_color(*current_color, brightness_factor)
                print(f"Intensidad ajustada a: {brightness_factor:.2f}")
            else:
                # Intensidad mínima alcanzada, resetear el brillo
                print("Intensidad mínima alcanzada. Reseteando brillo.")
                brightness_factor = 1.0  # Resetear el brillo a su valor inicial
                await set_color(*current_color, brightness_factor)
                intensity_reset = True  # Marcar que el brillo ha sido reseteado

        await asyncio.sleep(0.1)  # Reducción del tiempo de espera para hacer la disminución más rápida

async def run_led_system():
    global current_color_name, current_color, brightness_factor, led_off, touch_count, sensor_activated, intensity_reset

    # Configuración de pines
    red_pin = machine.PWM(machine.Pin(15))
    green_pin = machine.PWM(machine.Pin(14))
    blue_pin = machine.PWM(machine.Pin(13))
    sensor_pin = machine.Pin(17, machine.Pin.IN, machine.Pin.PULL_UP)
    button_pin = machine.Pin(2, machine.Pin.IN, machine.Pin.PULL_UP)

    # Configuración de PWM
    red_pin.freq(5000)
    green_pin.freq(5000)
    blue_pin.freq(5000)

    # Colores disponibles
    colors = {
        "blanco": (1, 1, 1),
        "rojo": (1, 0, 0),
        "morado": (1, 0, 1),
        "amarillo": (1, 1, 0),
        "rosado": (1, 0.5, 0.5),
        "verde": (0, 1, 0),
    }

    # Función para ajustar el brillo
    def adjust_brightness(color_value, factor):
        return max(0, min(65535, int(color_value * factor * 65535)))

    # Función para establecer el color
    async def set_color(red, green, blue, brightness_factor=1.0):
        red_pin.duty_u16(adjust_brightness(red, brightness_factor))
        green_pin.duty_u16(adjust_brightness(green, brightness_factor))
        blue_pin.duty_u16(adjust_brightness(blue, brightness_factor))

    print("Sistema listo. Presiona el botón para cambiar el color: ")

    await asyncio.gather(
        serial_controls(colors, set_color),
        button_controls(colors, set_color, button_pin),
        sensor_controls(sensor_pin, set_color)
    )

async def operations():
    await run_led_system()

async def main():
    await asyncio.gather(
        micro_monitoring.monitoring(get_app_data),   # Monitoreo del maestro
        operations()
    )

asyncio.run(main())
