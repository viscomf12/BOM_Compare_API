from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import io
import base64

app = FastAPI()

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Model JSON sesuai Power Automate =====
class PowerAutomateFile(BaseModel):
    __root__: dict  # akan ada "$content" dan "$content-type"

# ===== Fungsi load BOM =====
def load_bom(excel, sheet):
    df = pd.read_excel(excel, sheet_name=sheet)
    df = df[['PartNo', 'Qty']]
    df = df.groupby('PartNo', as_index=False).sum()
    return df

# ===== Endpoint utama =====
@app.post("/compare-bom-pa")
async def compare_bom_pa(file: PowerAutomateFile):
    try:
        # Ambil dictionary dari JSON Power Automate
        content_dict = file.__root__  # {'$content': ..., '$content-type': ...}
        
        # decode base64 menjadi bytes
        file_bytes = base64.b64decode(content_dict["$content"])
        
        # Baca Excel dari memory
        excel = pd.ExcelFile(io.BytesIO(file_bytes))

        # Ambil sheet bom1, bom2, bom3
        bom1 = load_bom(excel, 'bom1')
        bom2 = load_bom(excel, 'bom2')
        bom3 = load_bom(excel, 'bom3')

        # Merge semua BOM
        merged = bom1.merge(bom2, on='PartNo', how='outer', suffixes=('_bom1', '_bom2'))
        merged = merged.merge(bom3, on='PartNo', how='outer')
        merged = merged.rename(columns={'Qty': 'Qty_bom3'})
        merged = merged.fillna(0)

        # Tentukan status OK / MISMATCH
        def status(row):
            q = [row['Qty_bom1'], row['Qty_bom2'], row['Qty_bom3']]
            return "OK" if q[0] == q[1] == q[2] else "MISMATCH"

        merged['Status'] = merged.apply(status, axis=1)

        # === Generate Excel hasil compare di memory ===
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            merged.to_excel(writer, index=False, sheet_name='CompareResult')

        output.seek(0)
        encoded = base64.b64encode(output.read()).decode()

        return {
            "fileName": "BOM_Compare_Result.xlsx",
            "fileBase64": encoded
        }

    except Exception as e:
        return {"error": str(e)}
