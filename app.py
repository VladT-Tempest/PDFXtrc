import gradio as gr
import os
import tempfile
from pdf2image import convert_from_path
import logging
from commercial_invoice import process_invoice_batch, logger

def play_error_sound():
    """Reproduce un sonido de error usando winsound"""
    import winsound
    winsound.MessageBeep(winsound.MB_ICONHAND)

def procesar_pdf(pdf_path):
    """Procesa un archivo PDF y extrae información de las facturas"""
    try:
        # Validar que el nombre del archivo comience con "ci145"
        filename = os.path.basename(pdf_path).lower()
        if not filename.startswith("ci145"):
            error_msg = '<span style="color: red; font-weight: bold">⚠️ El tipo de archivo cargado no es compatible con el formato de extracción que maneja este programa, el cual está customizado para manejar únicamente los archivos que empiezan por "ci145".</span>'
            play_error_sound()
            logger.error("Archivo incompatible: " + filename)
            return error_msg, None

        # Crear directorio temporal para las imágenes
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Convirtiendo PDF a imágenes: {pdf_path}")
            
            # Convertir PDF a imágenes
            images = convert_from_path(pdf_path)
            image_paths = []
            
            # Guardar imágenes temporalmente
            for i, image in enumerate(images):
                image_path = os.path.join(temp_dir, f'pagina_{i+1}.jpg')
                image.save(image_path, 'JPEG')
                image_paths.append(image_path)
            
            logger.info(f"Se generaron {len(image_paths)} imágenes")
            
            # Procesar las imágenes
            coordinates_json = "./coordinates_CI.json"
            results_df = process_invoice_batch(image_paths, coordinates_json)
            
            # Guardar resultados
            output_dir = "./data"
            os.makedirs(output_dir, exist_ok=True)
            
            # Guardar archivo de facturas procesadas
            facturas_path = os.path.join(output_dir, 'facturas_procesadas.csv')
            results_df.to_csv(facturas_path, index=False)
            
            # Preparar mensaje de resultados
            mensaje = f"Procesamiento completado:\n"
            mensaje += f"- Páginas procesadas: {len(image_paths)}\n"
            mensaje += f"- Campos extraídos: {len(results_df.columns)-1}\n\n"
            mensaje += f"Archivos generados:\n"
            mensaje += f"1. Facturas procesadas: {facturas_path}\n"
            
            # Verificar archivo de productos
            productos_path = os.path.join(output_dir, 'productos_por_factura.csv')
            if os.path.exists(productos_path):
                mensaje += f"2. Productos por factura: {productos_path}"
            
            return mensaje, [facturas_path, productos_path]
            
    except Exception as e:
        error_msg = f'<span style="color: red; font-weight: bold">⚠️ Error durante el procesamiento: {str(e)}</span>'
        play_error_sound()
        logger.error(error_msg)
        return error_msg, None

def crear_interfaz():
    with gr.Blocks() as demo:
        gr.Markdown("# Extractor de Información de Facturas")
        
        with gr.Row():
            pdf_input = gr.File(
                label="Cargar PDF (el nombre debe empezar con 'ci145')",
                file_types=[".pdf"]
            )
        
        with gr.Row():
            procesar_btn = gr.Button("Procesar PDF")
        
        with gr.Row():
            output_text = gr.HTML(
                label="Resultados",
                value="Los resultados del procesamiento aparecerán aquí..."
            )
        
        with gr.Row():
            files_output = gr.File(
                label="Descargar archivos CSV",
                file_count="multiple",
                interactive=False,
                visible=False
            )
        
        def process_and_return(pdf_path):
            message, csv_files = procesar_pdf(pdf_path)
            return message, csv_files if csv_files else None
        
        procesar_btn.click(
            fn=process_and_return,
            inputs=[pdf_input],
            outputs=[output_text, files_output],
            show_progress=True
        ).then(
            lambda: gr.update(visible=True),
            None,
            [files_output]
        )
    
    return demo

if __name__ == "__main__":
    demo = crear_interfaz()
    demo.launch(share=True)