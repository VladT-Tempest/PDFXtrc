import os
from commercial_invoice import process_invoice
import logging

def get_line_number(item):
    """Extrae el número de línea del campo Product_line_X"""
    return int(item[0].split('_')[-1])

def test_single_invoice(pagina:str):
    # Configurar logging más detallado
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Definir rutas
    invoice_path = os.path.join("invoices", pagina)
    coordinates_json = "coordinates_CI.json"

    # Verificar que existe el archivo
    if not os.path.exists(invoice_path):
        logger.error(f"No se encontró el archivo: {invoice_path}")
        return

    # Procesar la factura
    logger.info("Iniciando prueba con factura individual...")
    try:
        results = process_invoice(invoice_path, coordinates_json, margin=5)

        # Mostrar resultados
        logger.info("\n=== RESULTADOS DE LA EXTRACCIÓN ===")
        
        # Primero mostrar campos generales
        logger.info("\n--- CAMPOS GENERALES ---")
        for field, value in sorted(results.items()):
            if not field.startswith("Product_line_"):
                logger.info(f"{field}: '{value}'")
        
        # Encontrar la última línea válida (la que está antes de la línea horizontal)
        max_valid_line = 0
        product_lines = [(k,v) for k,v in results.items() if k.startswith("Product_line_")]
        product_lines.sort(key=lambda x: int(x[0].split('_')[-1]))
        
        for field, _ in product_lines:
            line_num = int(field.split('_')[-1])
            if line_num > max_valid_line:
                max_valid_line = line_num
                
        logger.info("\n--- LÍNEAS DE PRODUCTO ---")
        for field, value in product_lines:
            line_num = int(field.split('_')[-1])
            if line_num <= max_valid_line:
                logger.info(f"{field}: '{value}' <-- PRODUCTO #{line_num}")
            
    except Exception as e:
        logger.error(f"Error en la prueba: {str(e)}", exc_info=True)

if __name__ == "__main__":
    test_single_invoice("pagina_2.jpg")