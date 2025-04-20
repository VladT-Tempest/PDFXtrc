import os
from commercial_invoice import process_invoice

def test_single_invoice():
    invoice_path = os.path.join("invoices", "pagina_5.jpg")
    coordinates_json = "coordinates_CI.json"

    print("Iniciando prueba con factura individual...")
    print(f"Procesando factura: {invoice_path}")

    try:
        # Procesar la factura
        results = process_invoice(invoice_path, coordinates_json, margin=5)

        # Verificar si se creó el archivo productos_por_factura.csv
        products_csv = os.path.join("data", "productos_por_factura.csv")
        print("\nVerificando resultados:")
        if os.path.exists(products_csv):
            print(f"✓ Archivo creado: {products_csv}")

            # Verificar contenido
            import pandas as pd
            df = pd.read_csv(products_csv)
            print(f"\nRegistros procesados: {len(df)}")
            
            # Mostrar algunos campos clave
            if not df.empty:
                print("\nPrimeras líneas procesadas:")
                print(df[["invoice_number", "Boxes", "Product_desc", "Stems"]].head())
        else:
            print("✗ El archivo de productos no se creó correctamente.")
        
    except Exception as e:
        print(f"Error en la prueba: {str(e)}")

if __name__ == "__main__":
    test_single_invoice()