import os
from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME") 

# Construct database URL                                                                                             
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=False)  # fast_executemany is for SQL Server, remove for MySQL
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ----------------------------
# MODELS
# ----------------------------

class PatientQuery(Base):
    __tablename__ = "PatientQueries"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    received_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    triage_category = Column(String(100))
    suggested_response = Column(Text)
    
    # relationships
    entities = relationship("ExtractedEntity", back_populates="query", cascade="all, delete-orphan")
    remarks = relationship("PatientRemark", back_populates="query", cascade="all, delete-orphan")
    routing_logs = relationship("RoutingLog", back_populates="query", cascade="all, delete-orphan")


class ExtractedEntity(Base):
    __tablename__ = "Extracted_Entities"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("PatientQueries.id"))
    entity_type = Column(String(50))
    entity_text = Column(String(500))
    
    query = relationship("PatientQuery", back_populates="entities")


class PatientRemark(Base):
    __tablename__ = "Patient_Remarks"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("PatientQueries.id"))
    remark_type = Column(String(50))
    remark_text = Column(String(500))
    
    query = relationship("PatientQuery", back_populates="remarks")


class RoutingLog(Base):
    __tablename__ = "Routing_Logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("PatientQueries.id"))
    department = Column(String(200))
    routed_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    agent_details = Column(Text)
    
    query = relationship("PatientQuery", back_populates="routing_logs")


# ----------------------------
# DATABASE INITIALIZATION
# ----------------------------
def init_db():
    Base.metadata.create_all(bind=engine)
    base.metadata.creat

