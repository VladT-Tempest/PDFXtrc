from pdf2image import   convert_from_path
from PIL import Image   
import pytesseract
import gradio as gr

def tesseract_ocr(filepath: str):
    """
    Perform OCR on the given image file and return the extracted text.
    """
    # Open the image file
    with Image.open(filepath) as img:
        # Use pytesseract to do OCR on the image
        text = pytesseract.image_to_string(img)
    return text 

title = "Invoicer IA"
description = "extract data from invoice"
article = "This is a simple OCR application that extracts text from images using Tesseract OCR. You can upload an image of an invoice, and the application will return the extracted text."
examples = [["example_invoice.png"]]  


with gr.Blocks(title=title) as demo:
    gr.Markdown(f'<h1 style="text-align: center; margin-bottom: 1rem;">{title}</h1>')
    gr.Markdown(description)
    gr.Markdown(article)

    with gr.Row():
        with gr.Column():
            image_input = gr.Image(type="filepath", label="Upload Invoice Image")
            output_text = gr.Textbox(label="Extracted Text", lines=10, placeholder="Extracted text will appear here...")

        with gr.Column():
            submit_button = gr.Button("Submit")
    
    
    submit_button.click(fn=tesseract_ocr, inputs=image_input, outputs=output_text)

if __name__ == "__main__":
    demo.launch()
    