from fastapi import FastAPI

from backend.database import Base, engine
from backend.models.user import User
from backend.models.company import Company
from backend.routes import auth, protected
from backend.models.email import Email
from backend.routes import auth, protected, email
from backend.routes import ai
from backend.routes import dashboard




#  Step 1: Create app FIRST
app = FastAPI(
    title="AI Customer Support SaaS",
    version="1.0.0"
)

#  Step 2: Create tables
Base.metadata.create_all(bind=engine)

#  Step 3: Include routes AFTER app
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(protected.router, prefix="/user", tags=["User"])
app.include_router(email.router, prefix="/email", tags=["Email"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])


# Root route
@app.get("/")
def read_root():
    return {"message": "SaaS Backend Running "}


# Health check
@app.get("/health")
def health_check():
    return {"status": "ok"}