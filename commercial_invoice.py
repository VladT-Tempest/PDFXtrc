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
        logging.FileHandler('invoice_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_field_areas(coordinates_json):
    """Carga y procesa las coordenadas desde el archivo JSON"""
    logger.debug(f"Cargando coordenadas desde: {coordinates_json}")
    try:
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
        logger.debug(f"Se cargaron {len(field_areas)} áreas de campos")
        return field_areas, data['width'], data['height']
    except Exception as e:
        logger.error(f"Error al cargar coordenadas: {str(e)}")
        raise

def extract_text_from_area(image, area, margin=10):
    """Extrae texto de un área específica de la imagen con margen de tolerancia"""
    logger.debug(f"Extrayendo texto del área: {area} con margen: {margin}")
    try:
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
        
        if not text:
            logger.debug("No se encontró texto en el área")
        else:
            logger.debug(f"Texto extraído: {text[:50]}...")
        return text
    except Exception as e:
        logger.error(f"Error al extraer texto: {str(e)}")
        return ""

def process_invoice(image_path, coordinates_json, margin=10):
    """Procesa la factura y extrae los campos con margen de tolerancia"""
    logger.info(f"Procesando factura: {image_path}")
    try:
        # Cargar imagen
        image = Image.open(image_path)
        
        # Cargar áreas de los campos
        field_areas, img_width, img_height = load_field_areas(coordinates_json)
        
        # Ajustar imagen si es necesario
        if image.size != (img_width, img_height):
            logger.debug(f"Redimensionando imagen de {image.size} a ({img_width}, {img_height})")
            image = image.resize((img_width, img_height))
        
        # Extraer texto de cada área
        extracted_fields = {}
        for label, area in field_areas.items():
            logger.debug(f"Procesando campo: {label}")
            text = extract_text_from_area(image, area, margin)
            if text:
                extracted_fields[label] = text
            else:
                logger.debug(f"Reintentando {label} con margen mayor")
                text = extract_text_from_area(image, area, margin * 2)
                if text:
                    extracted_fields[label] = text    

        # Agregar el nombre del archivo como identificador
        extracted_fields['filename'] = os.path.basename(image_path)
        
        logger.info(f"Extracción completada: {len(extracted_fields)} campos encontrados")
        return extracted_fields
    except Exception as e:
        logger.error(f"Error procesando factura {image_path}: {str(e)}")
        return {'filename': os.path.basename(image_path)}

if __name__ == "__main__":
    logger.info("Iniciando procesamiento de facturas")
    
    # Configurar directorios
    invoice_dir = "./invoices"
    data_dir = "./data"
    coordinates_json = "./coordinates_CI.json"
    
    # Crear directorio data si no existe
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    logger.debug(f"Directorio de datos creado: {data_dir}")
    
    # Lista para almacenar los resultados de todas las facturas
    all_results = []
    
    # Procesar todas las imágenes en el directorio
    total_files = len([f for f in os.listdir(invoice_dir) 
                      if f.endswith(('.jpg', '.jpeg', '.png'))])
    logger.info(f"Se encontraron {total_files} archivos para procesar")
    
    for filename in os.listdir(invoice_dir):
        if filename.endswith(('.jpg', '.jpeg', '.png')):
            image_path = os.path.join(invoice_dir, filename)
            results = process_invoice(image_path, coordinates_json, margin=5)
            all_results.append(results)
    
    # Crear DataFrame con todos los resultados
    df = pd.DataFrame(all_results)
    
    # Reordenar columnas (filename al inicio)
    cols = ['filename'] + [col for col in df.columns if col != 'filename']
    df = df[cols]
    
    # Guardar resultados en CSV
    csv_path = os.path.join(data_dir, 'ci_data.csv')
    df.to_csv(csv_path, index=False)
    
    logger.info(f"Proceso completado. Resultados guardados en: {csv_path}")
    logger.info(f"Total de facturas procesadas: {len(all_results)}")