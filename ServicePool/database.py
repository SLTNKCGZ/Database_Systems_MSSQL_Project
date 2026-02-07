from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "mssql+pyodbc://@DESKTOP-VHVTEIN/ServicePool?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
#DATABASE_URL = "mssql+pyodbc://@DESKTOP-MUCMHO1/ServicePool_2?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base=declarative_base()