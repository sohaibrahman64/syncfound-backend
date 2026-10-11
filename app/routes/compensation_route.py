from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from app.database import get_db
from app.models.compensation_model import CashEquityExpectation, ExpectedMinimumSalary, SalaryDuration, Currency
from app.models.country_new_model import CountryNew
from app.schemas.compensation_schema import CompensationCombinedResponse, CurrencyWithCountryResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Compensation"]
)


@router.get("/compensation", response_model=CompensationCombinedResponse)
def get_compensation(db: Session = Depends(get_db)):
    cash_equity_expectations = db.query(CashEquityExpectation).order_by(CashEquityExpectation.id.asc()).all()
    expected_minimum_salaries = db.query(ExpectedMinimumSalary).order_by(ExpectedMinimumSalary.id.asc()).all()
    salary_durations = db.query(SalaryDuration).order_by(SalaryDuration.id.asc()).all()

    # Query currencies with left join to CountryNew to get country_name and country_flag_path
    currency_results = db.query(
        Currency.currency_id,
        Currency.currency_code,
        Currency.currency_name,
        Currency.currency_symbol,
        Currency.is_active,
        Currency.created_at,
        Currency.updated_at,
        CountryNew.country_name.label('country_name'),
        CountryNew.country_flag_path.label('country_flag_path')
    ).outerjoin(
        CountryNew, Currency.currency_code == CountryNew.currency
    ).filter(
        or_(
            and_(Currency.currency_code == 'USD', CountryNew.country_name == 'United States'),
            and_(Currency.currency_code == 'GBP', CountryNew.country_name == 'United Kingdom'),
            and_(Currency.currency_code == 'EUR', CountryNew.country_name == 'Reunion'),
            Currency.currency_code.in_(['INR', 'PKR', 'CAD', 'SGD'])
        )
    ).order_by(Currency.currency_id.asc()).all()

    # Convert the currency results to the schema format
    currencies = []
    for row in currency_results:
        currency_dict = {
            "currency_id": row.currency_id,
            "currency_code": row.currency_code,
            "currency_name": row.currency_name,
            "currency_symbol": row.currency_symbol,
            "is_active": row.is_active,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "country_name": row.country_name,
            "country_flag_path": row.country_flag_path
        }
        currencies.append(CurrencyWithCountryResponse(**currency_dict))

    return CompensationCombinedResponse(
        cash_equity_expectations=cash_equity_expectations,
        expected_minimum_salaries=expected_minimum_salaries,
        salary_durations=salary_durations,
        currencies=currencies
    )