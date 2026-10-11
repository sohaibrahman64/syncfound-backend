from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CashEquityExpectationBase(BaseModel):
    cash_equity_expectation: str

class CashEquityExpectationCreate(CashEquityExpectationBase):
    pass

class CashEquityExpectationResponse(CashEquityExpectationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExpectedMinimumSalaryBase(BaseModel):
    expected_minimum_salary: str

class ExpectedMinimumSalaryCreate(ExpectedMinimumSalaryBase):
    pass

class ExpectedMinimumSalaryResponse(ExpectedMinimumSalaryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SalaryDurationBase(BaseModel):
    salary_duration: str

class SalaryDurationCreate(SalaryDurationBase):
    pass

class SalaryDurationResponse(SalaryDurationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CurrencyBase(BaseModel):
    currency_code: str
    currency_name: str
    currency_symbol: str
    is_active: bool

class CurrencyCreate(CurrencyBase):
    pass

class CurrencyResponse(CurrencyBase):
    currency_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schema for currency with joined country data
class CurrencyWithCountryResponse(CurrencyResponse):
    country_name: Optional[str] = None
    country_flag_path: Optional[str] = None

class CompensationCombinedResponse(BaseModel):
    cash_equity_expectations: list[CashEquityExpectationResponse]
    expected_minimum_salaries: list[ExpectedMinimumSalaryResponse]
    salary_durations: list[SalaryDurationResponse]
    currencies: list[CurrencyWithCountryResponse]