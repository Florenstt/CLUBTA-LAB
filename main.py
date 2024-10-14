import machine
import time
import ujson
import uasyncio as asyncio
import micro_monitoring

# Variables globales
current_color_name = "Apagado"
brightness_factor = 1.0
led_off = False
touch_count = 0
sensor_activated = False
current_color = (0, 0, 0)  # Inicialización del color actual
original_brightness_factor = brightness_factor  # Guardar el brillo original
start_time = None  # Inicialización de start_time

# Configura el puerto serial
uart = machine.UART(0, baudrate=115200)

def get_app_data():
    # Función que devuelve un `dict` con la data para el maestro.
    return {
        "color": current_color_name
    }

async def control_led_rgb():
    global current_color_name, brightness_factor, led_off, touch_count, sensor_activated, current_color, original_brightness_factor, start_time

    # Configura los pines para controlar el LED RGB
    red_pin = machine.PWM(machine.Pin(15))
    green_pin = machine.PWM(machine.Pin(14))
    blue_pin = machine.PWM(machine.Pin(13))

    # Establecer la frecuencia del PWM (por ejemplo, 1000 Hz)
    red_pin.freq(1000)
    green_pin.freq(1000)
    blue_pin.freq(1000)

    # Configura el pin del sensor táctil KY-027
    sensor_pin = machine.Pin(17, machine.Pin.IN, machine.Pin.PULL_UP)

    # Configura el pin del botón KY-004
    button_pin = machine.Pin(2, machine.Pin.IN, machine.Pin.PULL_UP)

    # Colores para el LED RGB (valores entre 0 y 1)
    colors = [
        ((1, 1, 1), "Blanco"),    # Blanco
        ((1, 0, 0), "Rojo"),      # Rojo
        ((1, 0, 1), "Morado"),    # Morado
        ((1, 1, 0), "Amarillo"),  # Amarillo
        ((1, 0.5, 0.5), "Rosado"),# Rosado
        ((0, 1, 0), "Verde"),     # Verde
    ]

    # Función para ajustar la intensidad del color (brightness)
    def adjust_brightness(color_value, factor):
        return max(0, min(65535, int(color_value * factor * 65535)))

    # Función para encender el color actual con una intensidad ajustada
    async def set_color(red, green, blue, brightness_factor=1.0):
        red_pin.duty_u16(adjust_brightness(red, brightness_factor))
        green_pin.duty_u16(adjust_brightness(green, brightness_factor))
        blue_pin.duty_u16(adjust_brightness(blue, brightness_factor))

    # Función para hacer una transición suave entre dos colores
    def smooth_transition(start_color, end_color, steps=20, delay=0.02):
        for i in range(steps + 1):
            red = start_color[0] + (end_color[0] - start_color[0]) * i / steps
            green = start_color[1] + (end_color[1] - start_color[1]) * i / steps
            blue = start_color[2] + (end_color[2] - start_color[2]) * i / steps
            await set_color(red, green, blue)
            time.sleep(delay)

    # Función para procesar comandos recibidos por el puerto serial
    def process_serial_command(command):
        global current_color, led_off, brightness_factor, current_color_name
        command = command.strip().lower()
        if command == "off":
            await set_color(0, 0, 0)
            led_off = True
            print("LED apagado por comando serial.")
        elif command == "on":
            led_off = False
            await set_color(*current_color, brightness_factor)
            print("LED encendido por comando serial.")
        elif command in ["blanco", "rojo", "morado", "amarillo", "rosado", "verde"]:
            for color, name in colors:
                if name.lower() == command:
                    current_color = color
                    current_color_name = name
                    await set_color(*current_color, brightness_factor)
                    print(f"Color cambiado a {name} por comando serial.")
                    break
        elif command.startswith("brightness"):
            _, value = command.split()
            brightness_factor = float(value)
            await set_color(*current_color, brightness_factor)
            print(f"Intensidad ajustada a {brightness_factor} por comando serial.")

    # Bucle principal
    while True:
        # Leer y procesar comandos seriales
        if uart.any():
            command = uart.readline().decode("utf-8").strip()
            print(f"Comando recibido: {command}")  # Log para ver el comando recibido
            process_serial_command(command)

        # Detecta si se toca el botón para contar toques
        if not button_pin.value():
            if start_time is None:
                start_time = time.ticks_ms()  # Asigna el tiempo de inicio
                touch_count = 1
                print("Toque detectado. Comenzando conteo de 5 segundos.")
                await asyncio.sleep(0.2)
            else:
                touch_count += 1
                print(f"Toque adicional detectado. Conteo actual: {touch_count}")
                await asyncio.sleep(0.2)
        else:
            if start_time and time.ticks_diff(time.ticks_ms(), start_time) >= 5000:
                # Cambia el color según la cantidad de toques detectados
                if touch_count == 1:
                    current_color = colors[0][0]  # Blanco
                    current_color_name = colors[0][1]  # Actualiza el nombre del color
                    print(f"Color seleccionado: {colors[0][1]}")
                elif touch_count == 2:
                    current_color = colors[1][0]  # Rojo
                    current_color_name = colors[1][1]  # Actualiza el nombre del color
                    print(f"Color seleccionado: {colors[1][1]}")
                elif touch_count == 3:
                    current_color = colors[2][0]  # Morado
                    current_color_name = colors[2][1]  # Actualiza el nombre del color
                    print(f"Color seleccionado: {colors[2][1]}")
                elif touch_count == 4:
                    current_color = colors[3][0]  # Amarillo
                    current_color_name = colors[3][1]  # Actualiza el nombre del color
                    print(f"Color seleccionado: {colors[3][1]}")
                elif touch_count == 5:
                    current_color = colors[4][0]  # Rosado
                    current_color_name = colors[4][1]  # Actualiza el nombre del color
                    print(f"Color seleccionado: {colors[4][1]}")
                elif touch_count == 6:
                    current_color = colors[5][0]  # Verde
                    current_color_name = colors[5][1]  # Actualiza el nombre del color
                    print(f"Color seleccionado: {colors[5][1]}")
                elif touch_count == 7:
                    print("Activando efecto multicolor")
                    for i in range(8):
                        for j in range(len(colors)):
                            start_color = colors[j][0]
                            end_color = colors[(j + 1) % len(colors)][0]
                            smooth_transition(start_color, end_color)
                            print(f"Transición de {colors[j][1]} a {colors[(j + 1) % len(colors)][1]}")
                    await set_color(*current_color, brightness_factor)
                    print("Efecto multicolor terminado. Puedes seleccionar otro color.")
                elif touch_count == 8:
                    await set_color(0, 0, 0)
                    print("Ocho toques detectados. Apagando el LED.")
                    led_off = True

                # Reiniciar los valores después de procesar toques
                if touch_count < 8:
                    touch_count = 0
                    start_time = None
                    await set_color(*current_color, brightness_factor)

        # Detecta cuando el sensor se activa (toque detectado)
        if not sensor_pin.value() and not led_off:
            if not sensor_activated:
                sensor_activated = True
                print("Sensor activado. Comenzando a disminuir intensidad.")
                await asyncio.sleep(0.2)
        else:
            if sensor_activated and not led_off:
                if brightness_factor > 0.1:
                    brightness_factor -= 0.1
                    await set_color(*current_color, brightness_factor)
                    print(f"Intensidad ajustada a: {brightness_factor:.1f}")
                else:
                    brightness_factor = 0.1
                    await set_color(*current_color, brightness_factor)
                    print("Intensidad mínima alcanzada. Esperando nueva entrada.")
                    sensor_activated = False
                    # Volver a la intensidad original después de alcanzar la intensidad mínima
                    brightness_factor = original_brightness_factor
                    await set_color(*current_color, brightness_factor)
                    print(f"Restableciendo intensidad a: {brightness_factor:.1f}")
            await asyncio.sleep(0.1)

async def operations():
    # Acá va todo el código específico del equipo.
    await control_led_rgb()

async def main():
    # Funcionamiento del equipo y monitoreo con el maestro se ejecutan concurrentemente.
    await asyncio.gather(
        operations(),
        micro_monitoring.monitoring(get_app_data)   # Monitoreo del maestro
    )

asyncio.run(main())
