from fastapi import FastAPI
from backend.routers import maps
<<<<<<< HEAD
=======
from backend.routers import forecast

>>>>>>> a0efdcb0befa519b9ca28e08b7bfa8445c20a3b0
app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


app.include_router(maps.router, prefix="/maps", tags=["Maps"])
<<<<<<< HEAD
=======
app.include_router(forecast.router, prefix="/maps", tags=["Maps"])
>>>>>>> a0efdcb0befa519b9ca28e08b7bfa8445c20a3b0
