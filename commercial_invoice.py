import json
from PIL import Image
import pytesseract
import pandas as pd
import os
from pathlib import Path
import logging
import re
import numpy as np
import cv2

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

def is_product_header(text):
    """Detecta si es la línea de encabezado de productos"""
    header_keywords = ['boxes', 'pieces', 'product', 'tariff', 'bunches', 'stems', 'unit', 'price']
    if text:
        text_lower = text.lower()
        return all(keyword in text_lower for keyword in header_keywords)
    return False

def is_horizontal_line(image_crop):
    """
    Detecta si una imagen contiene una línea horizontal
    
    Args:
        image_crop: Imagen recortada del área a analizar
        
    Returns:
        bool: True si se detecta una línea horizontal, False en caso contrario
        
    Notas:
        - Se considera una línea horizontal si al menos el 60% del ancho 
          contiene píxeles de línea continuos
        - Este umbral (0.6) fue determinado empíricamente y funciona bien 
          con diferentes calidades de escaneo
    """
    # Convertir a escala de grises si no lo está
    gray = cv2.cvtColor(np.array(image_crop), cv2.COLOR_RGB2GRAY)
    
    # Binarizar la imagen
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Detectar líneas horizontales
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (binary.shape[1]//2, 1))
    detected_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    
    # Contar líneas horizontales continuas
    row_sums = np.sum(detected_lines > 0, axis=1)
    max_continuous_line = np.max(row_sums) if row_sums.size > 0 else 0
    
    # Una línea continua debe ocupar al menos el 80% del ancho
    threshold = binary.shape[1] * 0.6
    
    logger.debug(f"Línea más larga detectada: {max_continuous_line} píxeles de {binary.shape[1]}")
    return max_continuous_line > threshold

def get_line_number(item):
    """Extrae el número de línea del nombre del campo"""
    try:
        return int(item[0].split('_')[-1])
    except:
        return 0

def extract_text_from_area(image, area, margin=10, is_product_line=False):
    """Extrae texto de un área específica de la imagen con margen de tolerancia"""
    try:
        # Aplicar margen a las coordenadas
        x1 = max(0, area["x1"] - margin)
        y1 = max(0, area["y1"] - margin)
        x2 = min(image.width, area["x2"] + margin)
        y2 = min(image.height, area["y2"] + margin)

        # Recortar la imagen
        crop = image.crop((x1, y1, x2, y2))

        # Si es línea de producto y detectamos línea horizontal, retornar None
        if is_product_line and is_horizontal_line(crop):
            logger.debug(f"Línea horizontal detectada en {x1},{y1}")
            return None

        # Configuración OCR
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(crop, lang='eng', config=custom_config).strip()
        
        return text
    except Exception as e:
        logger.error(f"Error al extraer texto: {str(e)}")
        return ""

def load_field_areas(coordinates_json):
    """Carga y procesa las coordenadas desde el archivo JSON"""
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
        return field_areas, data['width'], data['height']
    except Exception as e:
        logger.error(f"Error al cargar coordenadas: {str(e)}")
        raise

def process_invoice(image_path, coordinates_json, margin=5):
    """Procesa la factura y extrae los campos"""
    logger.info(f"Procesando factura: {image_path}")
    try:
        image = Image.open(image_path)
        field_areas, img_width, img_height = load_field_areas(coordinates_json)

        # Iniciar con el nombre del archivo
        extracted_fields = {'filename': os.path.basename(image_path)}
        
        # Ajustar imagen si es necesario
        if image.size != (img_width, img_height):
            image = image.resize((img_width, img_height))
        

        found_total_line = False
        last_valid_line = 0
        
        # Procesar campos generales primero
        for label, area in field_areas.items():
            if not label.startswith("Product_line_"):
                text = extract_text_from_area(image, area, margin)
                if text:
                    extracted_fields[label] = text
                    
        # Procesar líneas de producto hasta encontrar la línea horizontal
        product_fields = {k: v for k, v in field_areas.items() if k.startswith("Product_line_")}
        for label, area in sorted(product_fields.items(), 
                                key=lambda x: int(x[0].split('_')[-1])):
                                
            if found_total_line:
                break
                
            # Verificar si es línea horizontal
            if is_horizontal_line(image.crop((area["x1"], area["y1"], 
                                            area["x2"], area["y2"]))):
                found_total_line = True
                logger.debug(f"Línea horizontal detectada en {label}")
                break
                
            # Si no es línea horizontal, extraer texto
            text = extract_text_from_area(image, area, margin)
            if text:
                extracted_fields[label] = text
                last_valid_line = int(label.split('_')[-1])
                
        logger.info(f"Procesamiento completado. Última línea válida: {last_valid_line}")
        return extracted_fields
        
    except Exception as e:
        logger.error(f"Error procesando factura {image_path}: {str(e)}")
        return {'filename': os.path.basename(image_path)}
        
def process_invoice_batch(image_paths, coordinates_json, margin=5):
    """Procesa un lote de facturas"""
    logger.info(f"Iniciando procesamiento de {len(image_paths)} facturas")
    
    all_results = []
    for image_path in image_paths:
        results = process_invoice(image_path, coordinates_json, margin)
        all_results.append(results)
    
    df = pd.DataFrame(all_results)
    
    # Reordenar columnas
    if not df.empty and 'filename' in df.columns:
        cols = ['filename'] + [col for col in df.columns if col != 'filename']
        df = df[cols]
    
    return df

def main(invoice_dir="./invoices", data_dir="./data", coordinates_json="./coordinates_CI.json"):
    """Función principal"""
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    
    image_paths = [
        os.path.join(invoice_dir, f) 
        for f in os.listdir(invoice_dir) 
        if f.endswith(('.jpg', '.jpeg', '.png'))
    ]
    
    df = process_invoice_batch(image_paths, coordinates_json)
    
    if not df.empty:
        csv_path = os.path.join(data_dir, 'ci_data.csv')
        df.to_csv(csv_path, index=False)
        logger.info(f"Resultados guardados en: {csv_path}")
    
    return df

if __name__ == "__main__":
    main()