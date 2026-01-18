from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import io
import base64

# === INIT APP ===
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === HELPER FUNCTION TO LOAD BOM SHEETS ===
def load_bom(excel: pd.ExcelFile, sheet: str) -> pd.DataFrame:
    df = pd.read_excel(excel, sheet_name=sheet)
    df = df[['PartNo', 'Qty']]
    df = df.groupby('PartNo', as_index=False).sum()
    return df

# === REQUEST MODEL ===
class AttachmentContent(BaseModel):
    content: str = Field(..., alias='$content')
    content_type: str = Field(..., alias='$content-type')

# === API ENDPOINT ===
@app.post("/compare-bom-pa")
async def compare_bom_pa(body: AttachmentContent):
    try:
        # Decode base64 ke bytes
        file_bytes = base64.b64decode(body.content)
        excel = pd.ExcelFile(io.BytesIO(file_bytes))

        # Load BOM sheets
        bom1 = load_bom(excel, 'bom1')
        bom2 = load_bom(excel, 'bom2')
        bom3 = load_bom(excel, 'bom3')

        # Merge BOMs
        merged = bom1.merge(bom2, on='PartNo', how='outer', suffixes=('_bom1', '_bom2'))
        merged = merged.merge(bom3, on='PartNo', how='outer')
        merged = merged.rename(columns={'Qty': 'Qty_bom3'}).fillna(0)

        # Add Status
        def status(row):
            q = [row['Qty_bom1'], row['Qty_bom2'], row['Qty_bom3']]
            return "OK" if q[0] == q[1] == q[2] else "MISMATCH"

        merged['Status'] = merged.apply(status, axis=1)

        # Generate Excel in memory
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
