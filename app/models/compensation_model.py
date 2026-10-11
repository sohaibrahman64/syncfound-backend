import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean
from sqlalchemy.sql import func
from app.database import Base

class CashEquityExpectation(Base):
    __tablename__ = "cash_equity_expectations"

    id = Column(Integer, primary_key=True, index=True)
    cash_equity_expectation = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())


class ExpectedMinimumSalary(Base):
    __tablename__ = "expected_minimum_salary"

    id = Column(Integer, primary_key=True, index=True)
    expected_minimum_salary = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())


class SalaryDuration(Base):
    __tablename__ = "salary_duration"

    id = Column(Integer, primary_key=True, index=True)
    salary_duration = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())


class Currency(Base):
    __tablename__ = "currencies"

    currency_id = Column(Integer, primary_key=True, index=True)
    currency_code = Column(String, unique=True, index=True)
    currency_name = Column(String)
    currency_symbol = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())