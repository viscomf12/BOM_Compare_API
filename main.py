from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import io
import base64

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model JSON untuk menerima file dari Power Automate
class BOMFile(BaseModel):
    filename: str
    content: str  # base64 string

def load_bom(excel, sheet):
    df = pd.read_excel(excel, sheet_name=sheet)
    df = df[['PartNo', 'Qty']]
    df = df.groupby('PartNo', as_index=False).sum()
    return df

@app.post("/compare-bom-json")
async def compare_bom_json(file: BOMFile):
    try:
        # decode base64 menjadi bytes
        file_bytes = base64.b64decode(file.content)
        excel = pd.ExcelFile(io.BytesIO(file_bytes))

        bom1 = load_bom(excel, 'bom1')
        bom2 = load_bom(excel, 'bom2')
        bom3 = load_bom(excel, 'bom3')

        merged = bom1.merge(bom2, on='PartNo', how='outer', suffixes=('_bom1', '_bom2'))
        merged = merged.merge(bom3, on='PartNo', how='outer')
        merged = merged.rename(columns={'Qty': 'Qty_bom3'})
        merged = merged.fillna(0)

        def status(row):
            q = [row['Qty_bom1'], row['Qty_bom2'], row['Qty_bom3']]
            return "OK" if q[0] == q[1] == q[2] else "MISMATCH"

        merged['Status'] = merged.apply(status, axis=1)

        # === GENERATE EXCEL IN MEMORY ===
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            merged.to_excel(writer, index=False, sheet_name='CompareResult')

        output.seek(0)
        encoded = base64.b64encode(output.read()).decode()

        return {
            "fileName": f"BOM_Compare_Result_{file.filename}",
            "fileBase64": encoded
        }

    except Exception as e:
        return {"error": str(e)}
