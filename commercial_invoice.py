import json
from PIL import Image
import pytesseract

def load_field_areas(coordinates_json):
    """Carga y procesa las coordenadas desde el archivo JSON"""
    with open(coordinates_json, 'r') as f:
        data = json.load(f)
    
    field_areas = {}
    for box in data['boxes']:
        x = float(box['x'])
        y = float(box['y'])
        width = float(box['width'])
        height = float(box['height'])
        
        field_areas[box['label']] = {
            "x1": int(x - width/2),
            "y1": int(y - height/2),
            "x2": int(x + width/2),
            "y2": int(y + height/2)
        }
    return field_areas, data['width'], data['height']

def extract_text_from_area(image, area, margin=10):
    """Extrae texto de un área específica de la imagen con margen de tolerancia"""
    # Aplicar margen a las coordenadas
    x1 = max(0, area["x1"] - margin)
    y1 = max(0, area["y1"] - margin)
    x2 = min(image.width, area["x2"] + margin)
    y2 = min(image.height, area["y2"] + margin)

    # Recortar la imagen al área especificada
    crop = image.crop((x1, y1, x2, y2))

    # Configurar parámetros de OCR para mejor precisión
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(crop, lang='eng', config=custom_config).strip()
    return text

def process_invoice(image_path, coordinates_json, margin=10):
    """Procesa la factura y extrae los campos con margen de tolerancia"""
    # Cargar imagen
    image = Image.open(image_path)
    
    # Cargar áreas de los campos
    field_areas, img_width, img_height = load_field_areas(coordinates_json)
    
    # Ajustar imagen si es necesario
    if image.size != (img_width, img_height):
        image = image.resize((img_width, img_height))
    
    # Extraer texto de cada área
    extracted_fields = {}
    for label, area in field_areas.items():
        text = extract_text_from_area(image, area, margin)
        if text:
            extracted_fields[label] = text
        else:
            # Si no se encuentra texto, intentar con un margen mayor
            text = extract_text_from_area(image, area, margin * 2)
            if text:
                extracted_fields[label] = text    

    return extracted_fields

if __name__ == "__main__":
    # Rutas de archivos
    image_path = "./invoices/pagina_9.jpg"
    coordinates_json = "./coordinates_CI.json"
    
    # Procesar factura
    results = process_invoice(image_path, coordinates_json, margin=10)
    
    # Imprimir resultados
    print("\nCampos encontrados:")
    for field, value in results.items():
        print(f"{field}: {value}")