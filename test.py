import json
from PIL import Image
import pytesseract

def extract_text_from_area(image, area, margin=5):
    """Extrae texto de un área específica de la imagen"""
    try:
        # Aplicar margen a las coordenadas
        x1 = max(0, area["x1"] - margin)
        y1 = max(0, area["y1"] - margin)
        x2 = min(image.width, area["x2"] + margin)
        y2 = min(image.height, area["y2"] + margin)

        # Recortar la imagen al área especificada
        crop = image.crop((x1, y1, x2, y2))

        # Configurar OCR
        custom_config = r'--oem 3 --psm 6'
        return pytesseract.image_to_string(crop, lang='eng', config=custom_config).strip()
    except Exception as e:
        print(f"Error al extraer texto: {str(e)}")
        return ""

def test_single_invoice():
    """Prueba la extracción de campos en una sola factura"""
    try:
        # Rutas de archivos
        image_path = "./invoices/pagina_1.jpg"
        json_path = "./coordinates_CI.json"

        # Cargar imagen
        print(f"\nProcesando imagen: {image_path}")
        image = Image.open(image_path)

        # Cargar coordenadas
        print("Cargando coordenadas...")
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        # Procesar cada campo
        print("\nCampos encontrados:")
        print("-" * 50)

        for box in data['boxes']:
            # Calcular coordenadas
            x = float(box['x'])
            y = float(box['y'])
            width = float(box['width'])
            height = float(box['height'])

            area = {
                "x1": int(x - width/2),
                "y1": int(y - height/2),
                "x2": int(x + width/2),
                "y2": int(y + height/2)
            }

            # Extraer texto
            text = extract_text_from_area(image, area)
            if text:
                print(f"{box['label']}: {text}")

                  


    except FileNotFoundError:
        print("Error: No se encontró el archivo de imagen o coordenadas")
    except Exception as e:
        print(f"Error inesperado: {str(e)}")

if __name__ == "__main__":
    test_single_invoice()