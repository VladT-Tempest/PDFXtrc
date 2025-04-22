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


def is_horizontal_line(image_crop):
    """
    Detecta si una imagen contiene una línea horizontal
    """
    # Convertir a escala de grises si no lo está
    gray = cv2.cvtColor(np.array(image_crop), cv2.COLOR_RGB2GRAY)
    
    # Binarizar la imagen
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Detectar líneas horizontales
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    detected_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    
    # Contar líneas horizontales continuas
    row_sums = np.sum(detected_lines > 0, axis=1)
    max_continuous_line = np.max(row_sums) if row_sums.size > 0 else 0
    
    # Una línea continua debe ocupar al menos el 40% del ancho
    threshold = binary.shape[1] * 0.4
    
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

def process_product_line(text, invoice_number):
    """
    Procesa una línea de producto y retorna un diccionario con los valores extraídos
    """
    # Inicializar diccionario con valores vacíos
    product_data = {
        "invoice_number": invoice_number,
        "Boxes": "",
        "Pieces": "",
        "Product_code": "",
        "Product_desc": "",
        "Tariff_number": "",
        "Stems": "",
        "Unit_price": "",
        "Extended_price": ""
    }
    
    try:
        # Normalizar el texto para tipos de cajas específicos
        text = text.replace("HALF BOX", "HALF_BOX").replace("EIGTH BOX (1/8)", "EIGHT_BOX").replace("SIXTEENTH (1/16)", "SIXTEENTH_BOX")
        
        # Dividir la línea en partes
        parts = text.strip().split()
        
        if parts:
            current_idx = 0
            # Primera parte debe ser número decimal (cantidad de cajas)
            if any(c.isdigit() for c in parts[0]):
                product_data["Boxes"] = parts[0]
                current_idx = 1
                
                # Segunda parte es el tipo de caja (QUARTER, HALF_BOX, EIGHT_BOX)
                if current_idx < len(parts):
                    product_data["Pieces"] = parts[current_idx]
                    current_idx += 1
                
                # Si hay un tercer valor numérico, capturar
                if current_idx < len(parts) and parts[current_idx].isdigit():
                    product_data["Product_code"] = parts[current_idx]  
                    current_idx += 1
            
            # Capturar descripción del producto hasta encontrar código de tarifa
            product_desc = []
            while current_idx < len(parts):
                if re.match(r'\d{4}\.\d{2}\.\d{2}', parts[current_idx]) or \
                   re.match(r'\d{4}\.\d{2}\.\d{2}\.\d{2}', parts[current_idx]):
                    break
                product_desc.append(parts[current_idx])
                current_idx += 1
            product_data["Product_desc"] = " ".join(product_desc) if product_desc else ""
            
            # Número de tarifa
            if current_idx < len(parts):
                if re.match(r'\d{4}\.\d{2}\.\d{2}', parts[current_idx]) or \
                   re.match(r'\d{4}\.\d{2}\.\d{2}\.\d{2}', parts[current_idx]):
                    product_data["Tariff_number"] = parts[current_idx]
                    current_idx += 1
            
            # Stems
            if current_idx < len(parts):
                stems = parts[current_idx].replace(',', '')
                if stems.replace('.', '').isdigit():
                    product_data["Stems"] = stems
                    current_idx += 1
            
            # Unit price
            if current_idx < len(parts):
                unit_price = parts[current_idx]
                if unit_price.replace('.', '').isdigit():
                    product_data["Unit_price"] = unit_price
                    current_idx += 1
            
            # Extended price
            if current_idx < len(parts):
                ext_price = parts[current_idx]
                if ext_price.replace('.', '').isdigit():
                    product_data["Extended_price"] = ext_price
    
    except Exception as e:
        logger.error(f"Error procesando línea de producto: {text}")
        logger.error(str(e))
    
    return product_data

def process_invoice(image_path, coordinates_json, margin=5):
    """Procesa la factura y extrae los campos"""
    logger.info(f"Procesando factura: {image_path}")
    try:
        image = Image.open(image_path)
        field_areas, img_width, img_height = load_field_areas(coordinates_json)
        
        # Iniciar con el nombre del archivo
        extracted_fields = {'filename': os.path.basename(image_path)}
        products_data = []  # Lista para almacenar datos de productos
        found_total_line = False
        invoice_number = None
        
        # Ajustar imagen si es necesario
        if image.size != (img_width, img_height):
            image = image.resize((img_width, img_height))
        
        # Procesar campos generales primero (excluyendo Product_line_X)
        for label, area in field_areas.items():
            if not label.startswith("Product_line_"):
                text = extract_text_from_area(image, area, margin)
                if text:
                    extracted_fields[label] = text
                    if label == "invoice_number":
                        invoice_number = text
                        logger.info(f"Número de factura encontrado: {invoice_number}")
        
        # Procesar líneas de producto hasta encontrar la línea horizontal
        product_fields = {k: v for k, v in field_areas.items() 
                        if k.startswith("Product_line_")}
        
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
            
            # Si no es línea horizontal, procesar línea de producto
            text = extract_text_from_area(image, area, margin)
            if text:
                if invoice_number:  # Solo procesar si tenemos número de factura
                    product_data = process_product_line(text, invoice_number)
                    if any(product_data.values()):  # Si hay datos válidos
                        products_data.append(product_data)
                        logger.debug(f"Línea de producto procesada: {product_data}")
        
        # Guardar productos si hay datos nuevos
        if products_data:
            new_products_df = pd.DataFrame(products_data)
            csv_path = os.path.join("data", "productos_por_factura.csv")
            
            try:
                # Leer archivo existente
                existing_df = pd.read_csv(csv_path)
                # Agregar nuevos datos
                updated_df = pd.concat([existing_df, new_products_df], ignore_index=True)
                # Guardar todo en el archivo
                updated_df.to_csv(csv_path, index=False)
                logger.info(f"Productos agregados al archivo: {csv_path}")
            except Exception as e:
                logger.error(f"Error al actualizar archivo de productos: {str(e)}")
                # Si hay error, intentar guardar solo los nuevos datos
                new_products_df.to_csv(csv_path, mode='a', header=False, index=False)
        
        return extracted_fields
        
    except Exception as e:
        logger.error(f"Error procesando factura {image_path}: {str(e)}")
        return {'filename': os.path.basename(image_path)}

def process_invoice_batch(image_paths, coordinates_json):
    """Procesa un lote de imágenes de facturas"""
    logger.info(f"Iniciando procesamiento de {len(image_paths)} facturas")
    
    # Inicializar DataFrames vacíos al inicio del proceso por lotes
    products_df = pd.DataFrame(columns=[
        "invoice_number", "Boxes", "Pieces", "Product_desc", 
        "Tariff_number", "Stems", "Unit_price", "Extended_price"
    ])
    facturas_df = pd.DataFrame()
    
    # Crear archivos vacíos al inicio del proceso
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    products_csv_path = os.path.join(output_dir, "productos_por_factura.csv")
    facturas_csv_path = os.path.join(output_dir, "facturas_procesadas.csv")
    products_df.to_csv(products_csv_path, index=False)
    facturas_df.to_csv(facturas_csv_path, index=False)
    
    results = []
    for image_path in image_paths:
        try:
            result = process_invoice(image_path, coordinates_json)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Error procesando {image_path}: {str(e)}")
            results.append({'filename': os.path.basename(image_path)})

    df = pd.DataFrame(results)
    if not df.empty:
        df.to_csv(facturas_csv_path, index=False)
        logger.info(f"Resultados guardados en: {facturas_csv_path}")
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