from sqlmodel import SQLModel, Field
from typing import Optional, Dict, List, Any
from sqlalchemy import Enum, JSON, Column, ARRAY, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from .EasyModel import EasyModel, async_engine
#from src.routes.customer.get_brand import brandColors, contrastInfo, usedFonts, styleOfPictures, writingStyle, amountOfTextPerParagraph, websiteLogo, socialNetworks

# ADMIN TABLE DEFINITIONS
class APIKey(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    api_key: str = Field(max_length=255)
    model: str = Field(max_length=255)
    company: str = Field(default='OpenAI', max_length=255)
    max_tokens_per_min: int = Field(default=0)
    max_requests_per_min: int = Field(default=0)
    total_spent: float = Field(default=0.0)  # Total amount spent using this API key
    active: int = Field(default=1)  # 1 = active, 0 = inactive
    last_used: datetime = Field(default_factory=datetime.utcnow)
    last_error: Optional[str] = Field(default=None, max_length=255)
    last_health_check_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Record creation date
    updated_at: Optional[datetime] = Field(default=None)  # Record update date

class User(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, nullable=False, max_length=255)
    #hashed_password: str = Field(nullable=False, max_length=255)  # Store hashed passwords, not plain text
    password: str = Field(nullable=False, max_length=255)  # Store the non-hashed password as well for reference within admin
    type: str = Field(default='user', sa_column=Enum('user', 'admin', name='user_type'))
    session_ttl: int = Field(sa_column=Column(Integer, default=60, server_default='60'))  # Session TTL in minutes 
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ENDPOINT RELATED TABLES
class CustomerRecord(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_url: str = Field(nullable=False, max_length=512)
    name: str = Field(nullable=False, max_length=255)
    industry: str = Field(nullable=False, max_length=255)
    description: str = Field(nullable=False, max_length=1024)
    icp_query: Dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))   # JSON field for icp_query
    icp_profile: str = Field(nullable=False)  # Storing as a JSON string
    intent_samples: Dict[str, List[str]] = Field(sa_column=Column(JSON, nullable=False))  # JSON field for intent_samples
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

#extra data fields for the customer record
class CustomerRecordExtra(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_url: str = Field(nullable=False, max_length=512)
    name: str = Field(nullable=False, max_length=255)
    industry: str = Field(nullable=False, max_length=255)
    description: str = Field(nullable=False, max_length=1024)
    icp_query: Dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))   # JSON field for icp_query
    icp_profile: str = Field(nullable=False)  # Storing as a JSON string
    extra: Dict[str, Any] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

class CustomerOfferings(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_url: str = Field(nullable=False, max_length=512)
    type: str = Field(nullable=False, max_length=255, default='product')
    name: str = Field(nullable=False, max_length=255)
    description: str = Field(nullable=False, max_length=1024)
    price_per_month: float = Field(nullable=True, default=0.0)
    price_per_year: float = Field(nullable=True, default=0.0)
    free: bool = Field(nullable=True, default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

class CustomerKeywords(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_url: str = Field(nullable=False, max_length=512)
    overall: List[str] = Field(sa_column=Column(ARRAY(String)), description="List of top 10 overall website keywords")
    products: List[str] = Field(sa_column=Column(ARRAY(String)), description="List of top 5 keywords related to products")
    services: List[str] = Field(sa_column=Column(ARRAY(String)), description="List of top 5 keywords related to services")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

class CustomerContactInfo(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_url: str = Field(nullable=False, max_length=512)
    email: str = Field(nullable=True, max_length=512)
    email_support: str = Field(sa_column=Column(String, nullable=True))
    email_sales: str = Field(sa_column=Column(String, nullable=True))
    phone: str = Field(nullable=True, max_length=512)
    address: str = Field(nullable=True, max_length=512)
    country: str = Field(nullable=True, max_length=512)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

class CustomerFAQ(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_url: str = Field(nullable=False, max_length=512)
    question: str = Field(nullable=False, max_length=512)
    answer: str = Field(nullable=False, max_length=1024)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

class CustomerMissionValues(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_url: str = Field(nullable=False, max_length=512)
    mission: str = Field("", description="The mission statement of the customer")
    values: List[str] = Field(sa_column=Column(ARRAY(String)), description="A list of core values")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

class CustomerCompetitors(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True) 
    customer_url: str = Field(nullable=False, max_length=512)
    competitors: List[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
class CustomerBrandReport(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_url: str = Field(nullable=False, max_length=512)
    brand_colors: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    contrast_info: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    used_fonts: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    style_of_pictures: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    writing_style: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    amount_of_text_per_paragraph: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    website_logo: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    social_networks: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

##### EVENT LISTENERS #####
# Use SQLAlchemy's event system to update the timestamp automatically
from sqlalchemy import Enum, event
from sqlalchemy.orm import Session

# Update the updated_at timestamp for needed tables
@event.listens_for(Session, "before_flush")
def receive_before_flush(session, flush_context, instances):
    for instance in session.dirty:
        if isinstance(instance, User):
            instance.updated_at = datetime.utcnow()
        if isinstance(instance, APIKey):
            instance.updated_at = datetime.utcnow()
        if isinstance(instance, CustomerRecord):
            instance.updated_at = datetime.utcnow()
        if isinstance(instance, CustomerOfferings):
            instance.updated_at = datetime.utcnow()
        if isinstance(instance, CustomerContactInfo):
            instance.updated_at = datetime.utcnow()
        if isinstance(instance, CustomerFAQ):
            instance.updated_at = datetime.utcnow()
        if isinstance(instance, CustomerMissionValues):
            instance.updated_at = datetime.utcnow()
        if isinstance(instance, CustomerBrandReport):
            instance.updated_at = datetime.utcnow()
        if isinstance(instance, CustomerCompetitors):
            instance.updated_at = datetime.utcnow()

## Initialize the database
async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
