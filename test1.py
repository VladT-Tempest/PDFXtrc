import os
from hawb_processing import process_hawb

def test_single_hawb():
    hawb_path = os.path.join("hawb", "hawb_pagina_5.jpg")
    coordinates_json = "coordinates_HAWB.json"

    print("Iniciando prueba con GUIA individual...")
    print(f"Procesando guía: {hawb_path}")

    try:
        # Procesar la guía
        results = process_hawb(hawb_path, coordinates_json, margin=5)

     
        print("\nVerificando resultados:")
        # imprimir diccionario de resultados
        for key, value in results.items():
            print(f"{key}: {value}")
        
    except Exception as e:
        print(f"Error en la prueba: {str(e)}")

if __name__ == "__main__":
    test_single_hawb()