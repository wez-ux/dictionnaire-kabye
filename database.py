import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class MotKabye(Base):
    __tablename__ = 'mots_kabye'
    
    id = Column(Integer, primary_key=True)
    mot_kabye = Column(String(255), nullable=False)
    variantes_orthographiques = Column(Text)
    api = Column(String(100))
    traduction_francaise = Column(String(500), nullable=False)
    sens_multiple = Column(Text)
    synonymes = Column(Text)
    categorie_grammaticale = Column(String(100))
    sous_categorie = Column(String(100))
    origine_mot = Column(Text)
    exemple_usage = Column(Text)
    traduction_exemple = Column(Text)
    expressions_associees = Column(Text)
    notes_usage = Column(Text)
    image_url = Column(Text)
    verifie_par = Column(String(100))
    date_ajout = Column(DateTime, default=datetime.now)
    date_modification = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Champs de validation
    statut_validation = Column(String(50), default='en_attente')  # en_attente, valide, a_reviser, rejete
    notes_validation = Column(Text)
    date_validation = Column(DateTime)
    
    # Ajoutez un index pour les recherches de validation
    __table_args__ = (
        Index('idx_statut_validation', 'statut_validation'),
        Index('idx_verifie_par', 'verifie_par'),
    )

def get_database_url():
    # En production sur Render, utiliser la variable d'environnement
    if 'DATABASE_URL' in os.environ:
        return os.environ['DATABASE_URL']
    
    # En développement local avec SQLite
    return 'sqlite:///dictionnaire.db'

def init_db():
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    return engine

def get_session():
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()