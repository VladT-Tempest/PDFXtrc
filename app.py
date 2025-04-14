import gradio as gr
import os
import tempfile
from pdf2image import convert_from_path
import logging
from commercial_invoice import process_invoice_batch, logger

def procesar_pdf(pdf_path):
    """Procesa un archivo PDF y extrae información de las facturas"""
    try:
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
            csv_path = os.path.join(output_dir, 'facturas_procesadas.csv')
            results_df.to_csv(csv_path, index=False)
            
            # Preparar mensaje de resultados
            mensaje = f"Procesamiento completado:\n"
            mensaje += f"- Páginas procesadas: {len(image_paths)}\n"
            mensaje += f"- Campos extraídos: {len(results_df.columns)-1}\n"
            mensaje += f"- Archivo guardado: {csv_path}\n"
            
            return mensaje
            
    except Exception as e:
        error_msg = f"Error durante el procesamiento: {str(e)}"
        logger.error(error_msg)
        return error_msg

# Configurar interfaz Gradio..

def crear_interfaz():
    with gr.Blocks() as demo:
        gr.Markdown("# Extractor de Información de Facturas")
        
        with gr.Row():
            pdf_input = gr.File(label="Cargar PDF")
        
        with gr.Row():
            procesar_btn = gr.Button("Procesar PDF")
        
        with gr.Row():
            output_text = gr.Textbox(
                label="Resultados", 
                lines=10,
                placeholder="Los resultados del procesamiento aparecerán aquí..."
            )
        
        with gr.Row():
            csv_output = gr.File(
                label="Descargar CSV",
                interactive=False,
                visible=False
            )
        
        def process_and_return(pdf_path):
            message = procesar_pdf(pdf_path)
            csv_path = "./data/facturas_procesadas.csv"
            return message, csv_path if os.path.exists(csv_path) else None
        
        procesar_btn.click(
            fn=process_and_return,
            inputs=[pdf_input],
            outputs=[output_text, csv_output],
            show_progress=True
        ).then(
            lambda: gr.update(visible=True),
            None,
            [csv_output]
        )
    
    return demo


if __name__ == "__main__":
    demo = crear_interfaz()
    demo.launch(share=False)