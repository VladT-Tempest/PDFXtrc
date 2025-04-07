import gradio as gr
import sys

def greet(name):
    python_version = sys.version.split()[0]
    
    return f"Hello {name}!!\nPython version: {python_version}"

demo = gr.Interface(fn=greet, inputs="text", outputs="text")
demo.launch()
