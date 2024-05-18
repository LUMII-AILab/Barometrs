from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import default

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(default.router)