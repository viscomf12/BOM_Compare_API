from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI()

# === CORS FIX ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # sementara buka semua (aman untuk testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "running"}

def load_bom(excel, sheet):
    df = pd.read_excel(excel, sheet_name=sheet)
    df = df[['PartNo', 'Qty']]
    df = df.groupby('PartNo', as_index=False).sum()
    return df

@app.post("/compare-bom")
async def compare_bom(file: UploadFile = File(...)):
    try:
        content = await file.read()
        excel = pd.ExcelFile(io.BytesIO(content))

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

        return merged.to_dict(orient='records')

    except Exception as e:
        return {"error": str(e)}
