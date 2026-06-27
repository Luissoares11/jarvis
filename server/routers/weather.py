from fastapi import APIRouter, HTTPException, Depends

from server.auth import verify_token
from app.features.weather import get_weather_data

router = APIRouter()


@router.get("/weather")
def get_weather(location: str, days: int = 1, token: str = Depends(verify_token)):
    try:
        return get_weather_data(location, forecast_days=days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))