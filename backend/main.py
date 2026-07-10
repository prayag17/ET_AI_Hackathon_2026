from fastapi import FastAPI
from backend.routers import maps
from backend.routers import forecast
from backend.routers import advisory

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


app.include_router(maps.router, prefix="/maps", tags=["Maps"])
app.include_router(forecast.router, prefix="/maps", tags=["Maps"])
app.include_router(advisory.router, prefix="/maps", tags=["Maps"])
