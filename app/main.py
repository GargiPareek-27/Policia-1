from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, scans
from app.core.config import settings
app=FastAPI(title="Stroke Core–Penumbra Segmentation API",version="0.1.0",description="Hackathon prototype. Segmentation results are for demonstration/research only and require clinical validation before any medical use.")
app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_url],allow_credentials=True,allow_methods=["*"],allow_headers=["Authorization","Content-Type"])
app.include_router(auth.router,prefix="/api")
app.include_router(scans.router,prefix="/api")
app.include_router(scans.pathologist_router,prefix="/api")
app.include_router(scans.doctor_router,prefix="/api")
@app.get("/health",tags=["health"])
def health(): return {"status":"ok"}
