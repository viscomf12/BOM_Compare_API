from fastapi import FastAPI, UploadFile, File
import pandas as pd
import io

app = FastAPI()

@app.get("/")
def root():
    return {"status": "API running"}

@app.post("/compare-bom")
async def compare_bom(file: UploadFile = File(...)):
    content = await file.read()
    excel = pd.ExcelFile(io.BytesIO(content))

    bom1 = pd.read_excel(excel, sheet_name="bom1")
    bom2 = pd.read_excel(excel, sheet_name="bom2")
    bom3 = pd.read_excel(excel, sheet_name="bom3")

    return {
        "bom1_rows": len(bom1),
        "bom2_rows": len(bom2),
        "bom3_rows": len(bom3)
    }

