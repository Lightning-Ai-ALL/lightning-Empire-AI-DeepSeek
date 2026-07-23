from fastapi import FastAPI
from app.schemas import PredictionRequest, PredictionResponse
from app.model_lstm import predict_lstm
from app.database import SessionLocal, PredictionRecord
from app.analysis import generate_analysis_report
import uvicorn
from datetime import datetime

app = FastAPI(title="Wshao777 Wind Power LSTM API")

@app.post("/predict", response_model=PredictionResponse)
async def wind_predict(req: PredictionRequest):
    power_list, total_kwh = predict_lstm(req.hours)   # LSTM 預測
    avg_power = round(sum(power_list) / len(power_list), 2)
    
    # 存入資料庫
    db = SessionLocal()
    db.add(PredictionRecord(hours=req.hours, total_kwh=total_kwh, avg_power=avg_power, note="LSTM 預測"))
    db.commit()
    db.close()
    
    # 自動生成分析表
    report_path = generate_analysis_report()
    
    return {
        "status": "success",
        "predicted_power": power_list[:req.hours],
        "total_kwh": total_kwh,
        "message": f"LSTM 預測完成 | 報表: {report_path}"
    }

@app.get("/health")
async def health():
    return {"status": "ok", "hardware": "i3-7100 + GT1030", "model": "LSTM"}