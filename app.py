import gradio as gr
import os
import tempfile
from pdf2image import convert_from_path
import logging
from commercial_invoice import process_invoice_batch, logger
from hawb_processing import process_hawb_batch

# Configurar handler para capturar logs
class GradioHandler(logging.Handler):
    def __init__(self, log_history):
        super().__init__()
        self.log_history = log_history
        
    def emit(self, record):
        log_entry = self.format(record)
        self.log_history.append(log_entry)

def procesar_pdf_invoice(pdf_path, progress=gr.Progress()):
    """Procesa un archivo PDF y extrae información de las facturas"""
    log_history = []
    handler = GradioHandler(log_history)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    try:
        # Validar que el nombre del archivo comience con "ci145"
        filename = os.path.basename(pdf_path).lower()
        if not filename.startswith("ci145"):
            error_msg = """
            <div style='color: red; font-weight: bold; padding: 10px; border: 1px solid red; border-radius: 5px; background-color: #ffe6e6;'>
                ⚠️ El tipo de archivo cargado no es compatible con el formato de extracción que maneja este programa, el cual está customizado para manejar únicamente los archivos que empiezan por "ci145".
            </div>
            """
            logger.error("Archivo incompatible: " + filename)
            return error_msg, None, "\n".join(log_history)

        progress(0.1, desc="Iniciando procesamiento...")
        
        # Crear directorio temporal para las imágenes
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Convirtiendo PDF a imágenes: {pdf_path}")
            progress(0.2, desc="Convirtiendo PDF a imágenes...")
            
            # Convertir PDF a imágenes
            images = convert_from_path(pdf_path)
            image_paths = []
            
            # Guardar imágenes temporalmente
            for i, image in enumerate(images):
                progress((0.3 + (i/len(images) * 0.2)), desc=f"Procesando página {i+1} de {len(images)}...")
                image_path = os.path.join(temp_dir, f'pagina_{i+1}.jpg')
                image.save(image_path, 'JPEG')
                image_paths.append(image_path)
            
            logger.info(f"Se generaron {len(image_paths)} imágenes")
            progress(0.5, desc="Procesando imágenes...")
            
            # Procesar las imágenes
            coordinates_json = "./coordinates_CI.json"
            results_df = process_invoice_batch(image_paths, coordinates_json)
            
            progress(0.8, desc="Guardando resultados...")
            # Guardar resultados
            output_dir = "./data"
            os.makedirs(output_dir, exist_ok=True)
            
            # Guardar archivo de facturas procesadas
            facturas_path = os.path.join(output_dir, 'facturas_procesadas.csv')
            results_df.to_csv(facturas_path, index=False)
            
            progress(0.9, desc="Finalizando...")
            # Preparar mensaje de resultados con estilo
            mensaje = """
            <div style='padding: 10px; border: 1px solid #4CAF50; border-radius: 5px; background-color: #f1f8e9;'>
                <h3 style='color: #2E7D32; margin-top: 0;'>✅ Procesamiento completado</h3>
                <ul style='list-style-type: none; padding-left: 0;'>
                    <li>📄 Páginas procesadas: {}</li>
                    <li>📊 Campos extraídos: {}</li>
                </ul>
                <h4 style='color: #2E7D32;'>Archivos generados:</h4>
                <ol>
                    <li>facturas_procesadas.csv</li>
            """.format(len(image_paths), len(results_df.columns)-1)
            
            # Verificar archivo de productos
            productos_path = os.path.join(output_dir, 'productos_por_factura.csv')
            if os.path.exists(productos_path):
                mensaje += "<li>productos_por_factura.csv</li>"
            
            mensaje += "</ol></div>"
            
            progress(1.0, desc="¡Proceso completado!")
            return mensaje, [facturas_path, productos_path], "\n".join(log_history)
            
    except Exception as e:
        error_msg = f"""
        <div style='color: red; font-weight: bold; padding: 10px; border: 1px solid red; border-radius: 5px; background-color: #ffe6e6;'>
            ⚠️ Error durante el procesamiento: {str(e)}
        </div>
        """
        logger.error(error_msg)
        return error_msg, None, "\n".join(log_history)
    finally:
        logger.removeHandler(handler)

def procesar_guia_aerea(pdf_path, progress=gr.Progress()):
    """Procesa un archivo PDF de guía aérea y extrae las imágenes"""
    log_history = []
    handler = GradioHandler(log_history)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    try:
        # Validar que el nombre del archivo comience con "hawb145"
        filename = os.path.basename(pdf_path).lower()
        if not filename.startswith("hawb145"):
            error_msg = """
            <div style='color: red; font-weight: bold; padding: 10px; border: 1px solid red; border-radius: 5px; background-color: #ffe6e6;'>
                ⚠️ El archivo debe comenzar con "hawb145" para ser procesado como guía aérea.
            </div>
            """
            logger.error("Archivo incompatible: " + filename)
            return error_msg, None, "\n".join(log_history)

        progress(0.1, desc="Iniciando procesamiento...")
        
        # Usar directorio temporal para las imágenes
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Convirtiendo PDF a imágenes: {pdf_path}")
            progress(0.2, desc="Convirtiendo PDF a imágenes...")
            
            # Convertir PDF a imágenes
            images = convert_from_path(pdf_path)
            image_paths = []
            
            # Guardar imágenes en el directorio temporal
            for i, image in enumerate(images):
                progress((0.3 + (i/len(images) * 0.6)), desc=f"Procesando página {i+1} de {len(images)}...")
                image_path = os.path.join(temp_dir, f'hawb_pagina_{i+1}.jpg')
                image.save(image_path, 'JPEG')
                image_paths.append(image_path)
            
            logger.info(f"Se generaron {len(image_paths)} imágenes en directorio temporal")
            
            progress(0.5, desc="¡Proceso completado!")

            # Procesar las imágenes
            coordinates_json = "./coordinates_HAWB.json"    
            results_df = process_hawb_batch(image_paths, coordinates_json)

            output_dir = "data"
            os.makedirs(output_dir, exist_ok=True)
            csv_path = os.path.join(output_dir, 'hawb_procesados.csv')
            results_df.to_csv(csv_path, index=False)
            logger.info(f"Resultados guardados en: {csv_path}")
                     
            progress(0.9, desc="Finalizando...")
            
            # Preparar mensaje de resultados con estilo
            mensaje = f"""
            <div style='padding: 10px; border: 1px solid #4CAF50; border-radius: 5px; background-color: #f1f8e9;'>
                <h3 style='color: #2E7D32; margin-top: 0;'>✅ Procesamiento completado</h3>
                <ul style='list-style-type: none; padding-left: 0;'>
                    <li>📄 Páginas procesadas: {len(image_paths)}</li>
                    <li>📁 Imágenes procesadas en memoria temporal</li>
                </ul>
            </div>
            """
            
            return mensaje, csv_path, "\n".join(log_history)
            
    except Exception as e:
        error_msg = f"""
        <div style='color: red; font-weight: bold; padding: 10px; border: 1px solid red; border-radius: 5px; background-color: #ffe6e6;'>
            ⚠️ Error durante el procesamiento: {str(e)}
        </div>
        """
        logger.error(error_msg)
        return error_msg, None, "\n".join(log_history)
    finally:
        logger.removeHandler(handler)

def crear_interfaz():
    with gr.Blocks(css="""
        .message { margin-bottom: 20px; }
        .error { color: red; font-weight: bold; }
        .logs { 
            font-family: monospace; 
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            max-height: 200px;
            overflow-y: auto;
        }
        .tab-selected {
            border-bottom: 2px solid #2196F3 !important;
        }
    """) as demo:
        gr.Markdown("# Extractor de Información de Facturas y Guías Aéreas")
        
        with gr.Tabs() as tabs:
            with gr.TabItem("Facturas Comerciales", id=1):
                with gr.Row():
                    pdf_input = gr.File(
                        label="Cargar PDF de facturas (el nombre debe empezar con 'ci145')",
                        file_types=[".pdf"]
                    )
                
                with gr.Row():
                    procesar_facturas_btn = gr.Button(
                        "Procesar PDF de Facturas", 
                        variant="primary",
                        elem_classes=["custom-button"]
                    )
                
                with gr.Row():
                    output_text = gr.HTML(
                        label="Resultados"
                    )
                
                with gr.Row():
                    log_output = gr.Textbox(
                        label="Logs del proceso",
                        elem_classes=["logs"],
                        lines=10,
                        max_lines=10,
                        show_label=True
                    )
                
                with gr.Row():
                    files_output = gr.File(
                        label="Descargar archivos CSV",
                        file_count="multiple",
                        interactive=False,
                        visible=False
                    )
            
            with gr.TabItem("Guías Aéreas", id=2):
                with gr.Row():
                    guia_aerea_input = gr.File(
                        label="Cargar PDF de guía aérea. (El nombre debe empezar con 'hawb145')",
                        file_types=[".pdf"]
                    )
                
                with gr.Row():
                    procesar_guia_btn = gr.Button(
                        "Procesar PDF de Guías Aéreas", 
                        variant="primary",
                        elem_classes=["custom-button"]
                    )
                
                with gr.Row():
                    guia_output_text = gr.HTML(
                        label="Resultados"
                    )
                
                with gr.Row():
                    guia_log_output = gr.Textbox(
                        label="Logs del proceso",
                        elem_classes=["logs"],
                        lines=10,
                        max_lines=10,
                        show_label=True
                    )
                
                with gr.Row():
                    guia_files_output = gr.File(
                        label="Descargar archivos procesados",
                        file_count="multiple",
                        interactive=False,
                        visible=False
                    )
        
        def process_and_return_invoices(pdf_path):
            message, csv_files, logs = procesar_pdf_invoice(pdf_path)
            return message, csv_files if csv_files else None, logs
        
        def process_and_return_guia(pdf_path):
            message, files, logs = procesar_guia_aerea(pdf_path)
            return message, files if files else None, logs
        
        # Eventos de los botones
        procesar_facturas_btn.click(
            fn=process_and_return_invoices,
            inputs=[pdf_input],
            outputs=[output_text, files_output, log_output],
            show_progress=True
        ).then(
            lambda: gr.update(visible=True),
            None,
            [files_output]
        )
        
        procesar_guia_btn.click(
            fn=process_and_return_guia,
            inputs=[guia_aerea_input],
            outputs=[guia_output_text, guia_files_output, guia_log_output],
            show_progress=True
        ).then(
            lambda: gr.update(visible=True),
            None,
            [guia_files_output]
        )
    
    return demo

if __name__ == "__main__":
    demo = crear_interfaz()
    demo.launch(share=False)