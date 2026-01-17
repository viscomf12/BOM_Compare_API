from fastapi import FastAPI, UploadFile, File
import pandas as pd
import io

app = FastAPI()

@app.get("/")
def root():
    return {"status": "API running"}

@app.post("/compare-bom")
async def compare_bom(file: UploadFile = File(...)):
    excel = pd.ExcelFile(io.BytesIO(content))
    sheets = excel.sheet_names

    return {
        "sheets": sheets
    }


