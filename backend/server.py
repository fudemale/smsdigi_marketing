import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional

# ---- optional local .env loading (harmless on Render if not installed) ----
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError  # motor raises PyMongo errors

# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smsdigi-api")

app = FastAPI(title="SMS Marketing SaaS API")

# ----- Config (env vars) ----------------------------------------------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "sms")  # set this in Render to your chosen DB
# Comma-separated list, e.g. "https://smsdigi.com,https://www.smsdigi.com"
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "")

# Parse CORS origins from env, fallback to strict production origins;
# Render/Vercel preview URLs covered by regex below.
if CORS_ORIGINS_ENV.strip():
    ALLOW_ORIGINS = [o.strip() for o in CORS_ORIGINS_ENV.split(",") if o.strip()]
else:
    ALLOW_ORIGINS = [
        "https://smsdigi.com",
        "https://www.smsdigi.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- DB -------------------------------------------------------------------
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# ----- Models ---------------------------------------------------------------
class ContactForm(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    company: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None
    plan_interest: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Newsletter(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ----- Helpers --------------------------------------------------------------
def strip_mongo_id(doc: dict) -> dict:
    """Remove internal _id so Pydantic models accept the dict."""
    if not doc:
        return doc
    doc = dict(doc)
    doc.pop("_id", None)
    return doc

# Ensure indexes (runs once on startup)
@app.on_event("startup")
async def ensure_indexes() -> None:
    try:
        await db.command("ping")
        # unique email for newsletter
        await db.newsletter.create_index("email", unique=True)
        logger.info("Startup: DB connected and indexes ensured.")
    except Exception as e:
        logger.exception(f"Startup checks failed: {e}")

# ----- Routes ---------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "SMS Marketing SaaS API is running"}

@app.get("/api/health")
async def health_check():
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/api/contact", response_model=ContactForm)
async def submit_contact_form(contact: ContactForm):
    try:
        await db.contacts.insert_one(contact.model_dump())
        logger.info(f"New contact form submitted: {contact.email}")
        return contact
    except Exception as e:
        logger.exception(f"Error submitting contact form: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit contact form")

@app.post("/api/newsletter", response_model=Newsletter)
async def subscribe_newsletter(newsletter: Newsletter):
    try:
        # Rely on unique index; catch duplicates cleanly
        await db.newsletter.insert_one(newsletter.model_dump())
        logger.info(f"New newsletter subscription: {newsletter.email}")
        return newsletter
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email already subscribed")
    except Exception as e:
        logger.exception(f"Error subscribing to newsletter: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe to newsletter")

@app.get("/api/contacts", response_model=List[ContactForm])
async def get_contacts():
    try:
        contacts = await db.contacts.find().to_list(length=None)
        return [ContactForm(**strip_mongo_id(c)) for c in contacts]
    except Exception as e:
        logger.exception(f"Error fetching contacts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch contacts")

@app.get("/api/subscribers", response_model=List[Newsletter])
async def get_subscribers():
    try:
        subscribers = await db.newsletter.find().to_list(length=None)
        return [Newsletter(**strip_mongo_id(s)) for s in subscribers]
    except Exception as e:
        logger.exception(f"Error fetching subscribers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscribers")

# ----- Local dev entry ------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
