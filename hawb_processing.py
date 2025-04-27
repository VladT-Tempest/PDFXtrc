import json
from PIL import Image
import pytesseract
import pandas as pd
import os
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hawb_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
    x1 = max(0, area["x1"] - margin)
    y1 = max(0, area["y1"] - margin)
    x2 = min(image.width, area["x2"] + margin)
    y2 = min(image.height, area["y2"] + margin)
    crop = image.crop((x1, y1, x2, y2))
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(crop, lang='eng', config=custom_config).strip()
    return text

def process_hawb(image_path, coordinates_json, margin=5):
    """Procesa una imagen de HAWB y extrae los campos principales"""
    logger.info(f"Procesando HAWB: {image_path}")
    image = Image.open(image_path)
    field_areas, img_width, img_height = load_field_areas(coordinates_json)
    # Ajustar imagen si es necesario
    if image.size != (img_width, img_height):
        image = image.resize((img_width, img_height))
    # Extraer campos principales
    campos = ["Shipper_name", "hawb_number", "hawb_date", "number_pieces", "gross_weight", "kg_lb"]
    extracted = {"filename": os.path.basename(image_path)}
    for campo in campos:
        if campo in field_areas:
            extracted[campo] = extract_text_from_area(image, field_areas[campo], margin)
        else:
            extracted[campo] = ""
    return extracted

def process_hawb_batch(image_paths, coordinates_json):
    """Procesa un lote de imágenes de HAWB"""
    logger.info(f"Iniciando procesamiento de {len(image_paths)} HAWB")
    results = []
    for image_path in image_paths:
        try:
            result = process_hawb(image_path, coordinates_json)
            results.append(result)
        except Exception as e:
            logger.error(f"Error procesando {image_path}: {str(e)}")
            results.append({'filename': os.path.basename(image_path)})
    df = pd.DataFrame(results)
    return df
    

def main(hawb_dir="./hawb", data_dir="./data", coordinates_json="./coordinates_HAWB.json"):
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    image_paths = [
        os.path.join(hawb_dir, f)
        for f in os.listdir(hawb_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
    df = process_hawb_batch(image_paths, coordinates_json)
    return df

if __name__ == "__main__":
    main()
