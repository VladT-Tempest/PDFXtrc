from pdf2image import   convert_from_path
from PIL import Image   
import pytesseract
import gradio as gr
import os

def procesar_pdf(pdf_archivo):
    # Cear la carpeta "invoices" si no  existe
    carpeta_salida = "invoices"
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)

    # Convertir el PDF a imágenes
    paginas = convert_from_path(pdf_archivo, dpi=300)
    
    archivos_jpg = []
    
    for i, pagina in enumerate(paginas):
        # Guardar cada página como imagen JPG
        archivo_jpg = os.path.join(carpeta_salida, f"pagina_{i + 1}.jpg")
        pagina.save(archivo_jpg, "JPEG")
        archivos_jpg.append(archivo_jpg)    

    return f"PDF procesado. Las imágenes se guardaron en la carpeta '{carpeta_salida}'", archivos_jpg

interfaz = gr.Interface(
    fn=procesar_pdf,
    inputs=gr.File(label="Selecciona un archivo PDF"),
    outputs="text",
    title="Commercial Invoice data extraction",
    description="Takes a PDF file with commercial invoices and converts it to JPG images, then extracts the data from the images.",
    theme="default"
)

if __name__ == "__main__":
    interfaz.launch()