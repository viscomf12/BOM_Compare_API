from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import base64

# === INIT APP ===
app = FastAPI()

# === ENABLE CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === HELPER FUNCTION TO LOAD BOM SHEETS ===
def load_bom(excel: pd.ExcelFile, sheet: str) -> pd.DataFrame:
    """
    Load a BOM sheet, keep only 'PartNo' and 'Qty',
    and aggregate quantities by PartNo.
    """
    df = pd.read_excel(excel, sheet_name=sheet)
    df = df[['PartNo', 'Qty']]
    df = df.groupby('PartNo', as_index=False).sum()
    return df

# === API ENDPOINT TO COMPARE BOM FILE ===
@app.post("/compare-bom")
async def compare_bom(file: UploadFile = File(...)):
    try:
        # Read uploaded Excel file
        content = await file.read()
        excel = pd.ExcelFile(io.BytesIO(content))

        # Load BOM sheets
        bom1 = load_bom(excel, 'bom1')
        bom2 = load_bom(excel, 'bom2')
        bom3 = load_bom(excel, 'bom3')

        # Merge BOMs on 'PartNo'
        merged = bom1.merge(bom2, on='PartNo', how='outer', suffixes=('_bom1', '_bom2'))
        merged = merged.merge(bom3, on='PartNo', how='outer')
        merged = merged.rename(columns={'Qty': 'Qty_bom3'})
        merged = merged.fillna(0)

        # Add comparison status
        def status(row):
            q = [row['Qty_bom1'], row['Qty_bom2'], row['Qty_bom3']]
            return "OK" if q[0] == q[1] == q[2] else "MISMATCH"

        merged['Status'] = merged.apply(status, axis=1)

        # === GENERATE EXCEL IN MEMORY ===
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            merged.to_excel(writer, index=False, sheet_name='CompareResult')
        output.seek(0)

        # Encode Excel to Base64 for response
        encoded = base64.b64encode(output.read()).decode()

        return {
            "fileName": "BOM_Compare_Result.xlsx",
            "fileBase64": encoded
        }

    except Exception as e:
        return {"error": str(e)}
