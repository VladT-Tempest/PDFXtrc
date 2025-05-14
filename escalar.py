from PIL import Image
import os

def resize_image(page_number=1):
    # Definir dimensiones objetivo
    img_width = 2480  # Puedes ajustar estos valores según necesites
    img_height = 3509

    # Ruta de entrada y salida
    input_path = os.path.join('hawb', f'hawb_pagina_{page_number}.jpg')
    output_path = os.path.join('hawb', 'hawb_model.jpg')

    try:
        # Verificar si existe el archivo
        if not os.path.exists(input_path):
            print(f"No se encontró la imagen: {input_path}")
            return False

        # Abrir la imagen
        image = Image.open(input_path)
        
        # Ajustar imagen si es necesario
        if image.size != (img_width, img_height):
            image = image.resize((img_width, img_height))
        
        # Guardar la imagen redimensionada
        image.save(output_path)
        print(f"Imagen procesada exitosamente. Guardada como: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error al procesar la imagen: {str(e)}")
        return False

def main():
    page_number = 1
    while True:
        if resize_image(page_number):
            respuesta = input("¿Desea continuar con la siguiente iteración? (s/n): ")
            if respuesta.lower() != 's':
                print("Proceso finalizado.")
                break
            page_number += 1
        else:
            print("No hay más imágenes para procesar.")
            break

if __name__ == "__main__":
    main()