from fastapi import FastAPI
from app.database.config import database
from app.endpoints.health import router as health_router
from app.endpoints.dashboards import router as dashboards_router
from app.endpoints.widgets import router as widgets_router
# Si arreglas items, descomenta:
# from app.endpoints.items import router as items_router

app = FastAPI(title="Analytics & Dashboards", version="0.1.0")


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


app.include_router(health_router)
app.include_router(dashboards_router)
app.include_router(widgets_router)
# app.include_router(items_router)