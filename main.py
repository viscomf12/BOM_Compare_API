from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import io
import base64

app = FastAPI(title="BOM Compare API")

# Model untuk menerima file dari Power Automate
class PowerAutomateFile(BaseModel):
    filename: str
    content: str  # isi dari "$content"
    content_type: str  # isi dari "$content-type"

def load_bom(excel_file, sheet_name):
    """Baca sheet BOM dan gabungkan PartNo dengan sum Qty"""
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    df = df[['PartNo', 'Qty']]
    df = df.groupby('PartNo', as_index=False).sum()
    return df

@app.post("/compare-bom-json")
async def compare_bom_json(file: PowerAutomateFile):
    try:
        # Decode base64 dari Power Automate
        file_bytes = base64.b64decode(file.content)
        excel = pd.ExcelFile(io.BytesIO(file_bytes))

        # Load ketiga BOM
        bom1 = load_bom(excel, 'bom1')
        bom2 = load_bom(excel, 'bom2')
        bom3 = load_bom(excel, 'bom3')

        # Merge semua BOM
        merged = bom1.merge(bom2, on='PartNo', how='outer', suffixes=('_bom1', '_bom2'))
        merged = merged.merge(bom3, on='PartNo', how='outer')
        merged = merged.rename(columns={'Qty': 'Qty_bom3'})
        merged = merged.fillna(0)

        # Tambahkan kolom status
        merged['Status'] = merged.apply(
            lambda row: "OK" if row['Qty_bom1'] == row['Qty_bom2'] == row['Qty_bom3'] else "MISMATCH",
            axis=1
        )

        # Generate excel hasil di memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            merged.to_excel(writer, index=False, sheet_name='CompareResult')
        output.seek(0)
        encoded_result = base64.b64encode(output.read()).decode()

        # Kembalikan base64 hasil excel
        return {
            "fileName": f"BOM_Compare_Result_{file.filename}",
            "fileBase64": encoded_result
        }

    except Exception as e:
        return {"error": str(e)}
