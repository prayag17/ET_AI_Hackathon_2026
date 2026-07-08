from fastapi import FastAPI
<<<<<<< HEAD

=======
from backend.routers import maps
>>>>>>> df10704ebcf95f53795bcb41d20811040ef14c6c
app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
<<<<<<< HEAD
=======


app.include_router(maps.router, prefix="/maps", tags=["Maps"])
>>>>>>> df10704ebcf95f53795bcb41d20811040ef14c6c
