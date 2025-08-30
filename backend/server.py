from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional
import os
from datetime import datetime, timezone
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SMS Marketing SaaS API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('DB_NAME', 'sms_marketing_saas')

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Pydantic models
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

# Helper functions
def prepare_for_mongo(data):
    """Convert data for MongoDB storage"""
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k != '_id'}
    return data.dict(exclude={'_id'}) if hasattr(data, 'dict') else data

# Routes
@app.get("/")
async def root():
    return {"message": "SMS Marketing SaaS API is running"}

@app.get("/api/health")
async def health_check():
    try:
        # Test database connection
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/api/contact", response_model=ContactForm)
async def submit_contact_form(contact: ContactForm):
    try:
        contact_dict = prepare_for_mongo(contact)
        await db.contacts.insert_one(contact_dict)
        logger.info(f"New contact form submitted: {contact.email}")
        return contact
    except Exception as e:
        logger.error(f"Error submitting contact form: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit contact form")

@app.post("/api/newsletter", response_model=Newsletter)
async def subscribe_newsletter(newsletter: Newsletter):
    try:
        # Check if email already exists
        existing = await db.newsletter.find_one({"email": newsletter.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already subscribed")
        
        newsletter_dict = prepare_for_mongo(newsletter)
        await db.newsletter.insert_one(newsletter_dict)
        logger.info(f"New newsletter subscription: {newsletter.email}")
        return newsletter
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to newsletter: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe to newsletter")

@app.get("/api/contacts", response_model=List[ContactForm])
async def get_contacts():
    try:
        contacts = await db.contacts.find().to_list(length=None)
        return [ContactForm(**contact) for contact in contacts]
    except Exception as e:
        logger.error(f"Error fetching contacts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch contacts")

@app.get("/api/subscribers", response_model=List[Newsletter])
async def get_subscribers():
    try:
        subscribers = await db.newsletter.find().to_list(length=None)
        return [Newsletter(**subscriber) for subscriber in subscribers]
    except Exception as e:
        logger.error(f"Error fetching subscribers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscribers")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)