import numpy as np
from PIL import Image, ImageDraw, ImageFont
import tensorflow as tf
import requests
import time

LETRAS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ESP32_IP = "10.27.24.198"  # cambia por la IP que muestre el Serial Monitor

print("Cargando modelo...")
model = tf.keras.models.load_model("modelo_letras.h5")
print("Modelo listo.\n")

def generar_imagen_palabra(palabra):
    ancho = 28 * len(palabra)
    img_palabra = Image.new('L', (ancho, 28), color=0)

    for i, letra in enumerate(palabra):
        img_letra = Image.new('L', (28, 28), color=0)
        draw = ImageDraw.Draw(img_letra)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
            except:
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), letra, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (28 - w) // 2
        y = (28 - h) // 2
        draw.text((x, y), letra, fill=255, font=font)
        img_palabra.paste(img_letra, (i * 28, 0))

    img_palabra.save(f"palabra_{palabra}.png")
    img_palabra.show()
    return img_palabra

def generar_imagen_letra(letra):
    img = Image.new('L', (28, 28), color=0)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
        except:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), letra, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (28 - w) // 2
    y = (28 - h) // 2
    draw.text((x, y), letra, fill=255, font=font)

    return np.array(img).reshape(1, 28, 28, 1) / 255.0

def predecir(letra):
    img = generar_imagen_letra(letra)
    pred = model.predict(img, verbose=0)
    idx = np.argmax(pred)
    confianza = pred[0][idx] * 100
    return LETRAS[idx], confianza

def enviar_letra(letra):
    try:
        r = requests.get(f"http://{ESP32_IP}/letra?l={letra}", timeout=30)
        if r.status_code == 200:
            print(f"  ESP32 OK")
        else:
            print(f"  ESP32 error: {r.status_code}")
    except Exception as e:
        print(f"  Sin conexion ESP32: {e}")

def main():
    print("=== SISTEMA LSC ===")
    print("Escribe una palabra y presiona Enter")
    print("Ctrl+C para salir\n")

    while True:
        texto = input(">> ").strip().upper()
        if not texto:
            continue

        print(f"\nProcesando: {texto}\n")

        # Generar imagen de la palabra completa
        palabras = texto.split(' ')
        for palabra in palabras:
            if palabra:
                generar_imagen_palabra(palabra)

        # Predecir y enviar letra por letra
        for letra in texto:
            if letra == ' ':
                print("  (espacio)\n")
                time.sleep(1)
                continue

            prediccion, confianza = predecir(letra)

            print(f"  Letra real:   {letra}")
            print(f"  Prediccion:   {prediccion} ({confianza:.1f}%)")

            if prediccion == letra:
                print(f"  Correcto!")
            else:
                print(f"  Diferente")

            print(f"  Enviando '{prediccion}' al ESP32...")
            enviar_letra(prediccion)
            print()

        print(f"'{texto}' completado.\n")

if __name__ == "__main__":
    main()