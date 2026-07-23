from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

engine = create_engine("sqlite:///wind_predictions.db", echo=False)
Base = declarative_base()

class PredictionRecord(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    hours = Column(Integer)
    total_kwh = Column(Float)
    avg_power = Column(Float)
    note = Column(String)

Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)