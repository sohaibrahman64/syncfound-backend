import os
from datetime import datetime, timezone

import requests

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError  # type: ignore
from sqlalchemy.orm import Session # type: ignore

from app.database import get_db
from app.models.city_model import City
from app.models.country_new_model import CountryNew
from app.models.country_model import Country
from app.models.state_model import State
from app.models.state_sync_checkpoint_model import StateSyncCheckpoint
from app.schemas.country_schema import (
    BackfillStateCheckpointsResponse,
    CitySyncFailure,
    CityLookupByCountryCodeResponse,
    CountryNewResponse,
    CountryResponse,
    CountrySyncFailure,
    DownloadCountryFlagsResponse,
    FlagDownloadFailure,
    StateLookupByCountryCodeRequest,
    StateLookupByCountryCodeResponse,
    StateSyncFailure,
    SyncCitiesResponse,
    SyncCountriesNewResponse,
    SyncStatesResponse,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["Countries"]

)

@router.get("/countries", response_model=list[CountryResponse])
def get_countries(db: Session = Depends(get_db)):
    countries = db.query(Country).order_by(Country.country_name.asc()).all()
    return countries


@router.get("/countries-new", response_model=list[CountryNewResponse])
def get_countries_new(db: Session = Depends(get_db)):
    countries = db.query(CountryNew).order_by(CountryNew.country_name.asc()).all()
    return countries


@router.post("/countries/states/by-country-code", response_model=StateLookupByCountryCodeResponse)
def get_states_by_country_code(
    payload: StateLookupByCountryCodeRequest,
    db: Session = Depends(get_db),
):
    iso3 = payload.iso3.strip().upper()
    phone_code = payload.phone_code.strip()

    if not iso3 or not phone_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both iso3 and phone_code are required.",
        )

    country = (
        db.query(CountryNew)
        .filter(
            CountryNew.iso3 == iso3,
            CountryNew.phone_code == phone_code,
        )
        .first()
    )

    if country is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found for the provided iso3 and phone_code.",
        )

    states = (
        db.query(State)
        .filter(
            State.country_id == country.id,
            State.is_active.is_(True),
        )
        .order_by(State.state_name.asc())
        .all()
    )

    return StateLookupByCountryCodeResponse(
        country_id=country.id,
        country_name=country.country_name,
        iso2=country.iso2,
        iso3=country.iso3,
        phone_code=country.phone_code,
        states=states,
    )


@router.post("/countries/cities/by-country-code", response_model=CityLookupByCountryCodeResponse)
def get_cities_by_country_code(
    payload: StateLookupByCountryCodeRequest,
    db: Session = Depends(get_db),
):
    iso3 = payload.iso3.strip().upper()
    phone_code = payload.phone_code.strip()

    if not iso3 or not phone_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both iso3 and phone_code are required.",
        )

    country = (
        db.query(CountryNew)
        .filter(
            CountryNew.iso3 == iso3,
            CountryNew.phone_code == phone_code,
        )
        .first()
    )

    if country is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found for the provided iso3 and phone_code.",
        )

    cities = (
        db.query(City)
        .filter(
            City.country_id == country.id,
            City.is_active.is_(True),
        )
        .order_by(City.city_name.asc())
        .all()
    )

    return CityLookupByCountryCodeResponse(
        country_id=country.id,
        country_name=country.country_name,
        iso2=country.iso2,
        iso3=country.iso3,
        phone_code=country.phone_code,
        cities=cities,
    )


@router.post("/countries/cities/sync", response_model=SyncCitiesResponse)
def sync_cities(db: Session = Depends(get_db)):
    try:
        response = requests.get(
            "https://countriesnow.space/api/v0.1/countries",
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch cities data: {exc}",
        ) from exc

    if payload.get("error") is True:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Countries API returned an error: {payload.get('msg', 'unknown')}",
        )

    data = payload.get("data")
    if not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected API response format.",
        )

    country_map = {
        c.iso2: c
        for c in db.query(CountryNew).filter(CountryNew.iso2.isnot(None)).all()
    }

    failures: list[CitySyncFailure] = []
    cities_inserted = 0
    cities_updated = 0
    countries_processed = 0
    countries_skipped = 0

    for entry in data:
        if not isinstance(entry, dict):
            continue

        iso2 = str(entry.get("iso2", "")).strip().upper()
        if not iso2:
            failures.append(CitySyncFailure(country_iso="", reason="Missing iso2 in API response entry."))
            continue

        country = country_map.get(iso2)
        if country is None:
            countries_skipped += 1
            continue

        cities_list = entry.get("cities", [])
        if not isinstance(cities_list, list):
            failures.append(CitySyncFailure(country_iso=iso2, reason="cities field is not a list."))
            continue

        try:
            existing_city_names = {
                row[0]
                for row in db.query(City.city_name)
                .filter(City.country_id == country.id)
                .all()
            }

            for city_name_raw in cities_list:
                city_name = str(city_name_raw).strip()
                if not city_name:
                    continue

                if city_name not in existing_city_names:
                    db.add(
                        City(
                            country_id=country.id,
                            city_name=city_name,
                            is_active=True,
                        )
                    )
                    cities_inserted += 1
                    existing_city_names.add(city_name)
                else:
                    updated = (
                        db.query(City)
                        .filter(
                            City.country_id == country.id,
                            City.city_name == city_name,
                            City.is_active.is_(False),
                        )
                        .first()
                    )
                    if updated is not None:
                        updated.is_active = True
                        cities_updated += 1

            db.commit()
            countries_processed += 1
        except SQLAlchemyError as exc:
            db.rollback()
            failures.append(CitySyncFailure(country_iso=iso2, reason=f"DB error: {str(exc)[:500]}"))

    return SyncCitiesResponse(
        message="Cities sync completed.",
        countries_processed=countries_processed,
        countries_failed=len(failures),
        countries_skipped=countries_skipped,
        cities_inserted=cities_inserted,
        cities_updated=cities_updated,
        failures=failures,
    )


@router.post("/countries-new/sync", response_model=SyncCountriesNewResponse)
def sync_countries_new(db: Session = Depends(get_db)):
    api_key = os.getenv("COUNTRY_STATE_CITY_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="COUNTRY_STATE_CITY_API_KEY is not configured.",
        )

    try:
        response = requests.get(
            "https://api.countrystatecity.in/v1/countries",
            headers={"X-CSCAPI-KEY": api_key},
            timeout=30,
        )
        response.raise_for_status()
        countries_payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch countries: {exc}",
        ) from exc

    if not isinstance(countries_payload, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected API response format.",
        )

    failures: list[CountrySyncFailure] = []
    countries_inserted = 0
    countries_updated = 0

    try:
        for country_item in countries_payload:
            if not isinstance(country_item, dict):
                continue

            iso2 = str(country_item.get("iso2", "")).strip().upper()
            identifier = iso2 or str(country_item.get("name", "unknown"))
            country_name = str(country_item.get("name", "")).strip()

            if not iso2 or not country_name:
                failures.append(CountrySyncFailure(identifier=identifier, reason="Missing required country fields."))
                continue

            iso3_value = country_item.get("iso3")
            phone_code_value = country_item.get("phonecode")
            capital_value = country_item.get("capital")
            currency_value = country_item.get("currency")
            native_value = country_item.get("native")
            emoji_value = country_item.get("emoji")
            emoji_u_value = country_item.get("emojiU")

            iso3 = str(iso3_value).strip().upper() if iso3_value else None
            phone_code = str(phone_code_value).strip() if phone_code_value else None
            capital = str(capital_value).strip() if capital_value else None
            currency = str(currency_value).strip().upper() if currency_value else None
            native_name = str(native_value).strip() if native_value else None
            emoji = str(emoji_value).strip() if emoji_value else None
            emoji_u = str(emoji_u_value).strip() if emoji_u_value else None

            country_record = db.query(CountryNew).filter(CountryNew.iso2 == iso2).first()

            if country_record is None:
                db.add(
                    CountryNew(
                        country_name=country_name,
                        iso2=iso2,
                        iso3=iso3,
                        phone_code=phone_code,
                        capital=capital,
                        currency=currency,
                        native_name=native_name,
                        emoji=emoji,
                        emoji_u=emoji_u,
                        is_active=True,
                    )
                )
                countries_inserted += 1
                continue

            has_changes = False
            if country_record.country_name != country_name:
                country_record.country_name = country_name
                has_changes = True
            if country_record.iso3 != iso3:
                country_record.iso3 = iso3
                has_changes = True
            if country_record.phone_code != phone_code:
                country_record.phone_code = phone_code
                has_changes = True
            if country_record.capital != capital:
                country_record.capital = capital
                has_changes = True
            if country_record.currency != currency:
                country_record.currency = currency
                has_changes = True
            if country_record.native_name != native_name:
                country_record.native_name = native_name
                has_changes = True
            if country_record.emoji != emoji:
                country_record.emoji = emoji
                has_changes = True
            if country_record.emoji_u != emoji_u:
                country_record.emoji_u = emoji_u
                has_changes = True
            if country_record.is_active is not True:
                country_record.is_active = True
                has_changes = True

            if has_changes:
                countries_updated += 1

        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save countries_new data: {exc}",
        ) from exc

    return SyncCountriesNewResponse(
        message="countries_new sync completed.",
        countries_inserted=countries_inserted,
        countries_updated=countries_updated,
        countries_failed=len(failures),
        failures=failures,
    )


@router.post("/countries-new/flags/download", response_model=DownloadCountryFlagsResponse)
def download_countries_new_flags(db: Session = Depends(get_db)):
    destination_path = r"D:\Hinduja\SyncFound\codebase\syncfound-mobile-frontend\assets\flags_new"
    os.makedirs(destination_path, exist_ok=True)

    countries = db.query(CountryNew).filter(CountryNew.iso2.isnot(None)).all()
    if not countries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No countries found in countries_new.",
        )

    failures: list[FlagDownloadFailure] = []
    flags_downloaded = 0
    countries_processed = 0

    for country in countries:
        iso2 = (country.iso2 or "").strip().upper()
        if not iso2:
            failures.append(FlagDownloadFailure(iso2="", reason=f"Missing iso2 for row id {country.id}"))
            continue

        url = f"https://flagcdn.com/w320/{iso2.lower()}.png"
        file_path = os.path.join(destination_path, f"{iso2.lower()}.png")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(file_path, "wb") as file_obj:
                file_obj.write(response.content)

            country.country_flag_path = file_path
            flags_downloaded += 1
            countries_processed += 1
        except (requests.RequestException, OSError) as exc:
            failures.append(FlagDownloadFailure(iso2=iso2, reason=str(exc)))

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update countries_new flag paths: {exc}",
        ) from exc

    return DownloadCountryFlagsResponse(
        message="countries_new flags download completed.",
        countries_processed=countries_processed,
        flags_downloaded=flags_downloaded,
        countries_failed=len(failures),
        destination_path=destination_path,
        failures=failures,
    )


@router.post("/countries/states/checkpoints/backfill", response_model=BackfillStateCheckpointsResponse)
def backfill_state_sync_checkpoints(db: Session = Depends(get_db)):
    countries = db.query(CountryNew).filter(CountryNew.iso2.isnot(None)).all()
    if not countries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No countries found in countries_new.",
        )

    state_country_ids = {
        row[0]
        for row in db.query(State.country_id).distinct().all()
        if row[0] is not None
    }

    now = datetime.now(timezone.utc)
    checkpoints_created = 0
    checkpoints_updated = 0
    countries_with_states = 0

    try:
        for country in countries:
            if country.id not in state_country_ids:
                continue

            countries_with_states += 1
            iso2 = (country.iso2 or "").strip().upper()

            checkpoint = (
                db.query(StateSyncCheckpoint)
                .filter(StateSyncCheckpoint.country_new_id == country.id)
                .first()
            )

            if checkpoint is None:
                checkpoint = StateSyncCheckpoint(
                    country_new_id=country.id,
                    iso2=iso2,
                    sync_status="success",
                    attempt_count=1,
                    last_error=None,
                    last_attempt_at=now,
                    last_success_at=now,
                )
                db.add(checkpoint)
                checkpoints_created += 1
                continue

            checkpoint.iso2 = iso2
            checkpoint.sync_status = "success"
            checkpoint.last_error = None
            checkpoint.last_success_at = now
            if checkpoint.attempt_count is None or checkpoint.attempt_count < 1:
                checkpoint.attempt_count = 1
            if checkpoint.last_attempt_at is None:
                checkpoint.last_attempt_at = now
            checkpoints_updated += 1

        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to backfill checkpoints: {exc}",
        ) from exc

    return BackfillStateCheckpointsResponse(
        message="state_sync_checkpoints backfill completed.",
        countries_scanned=len(countries),
        countries_with_states=countries_with_states,
        countries_without_states=len(countries) - countries_with_states,
        checkpoints_created=checkpoints_created,
        checkpoints_updated=checkpoints_updated,
    )


@router.post("/countries/states/sync", response_model=SyncStatesResponse)
def sync_states(
    request_limit: int = Query(default=95, ge=1, le=100),
    db: Session = Depends(get_db),
):
    api_key = os.getenv("COUNTRY_STATE_CITY_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="COUNTRY_STATE_CITY_API_KEY is not configured.",
        )

    countries = db.query(CountryNew).filter(CountryNew.iso2.isnot(None)).all()
    if not countries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No countries found to sync states.",
        )

    failures: list[StateSyncFailure] = []
    states_inserted = 0
    states_updated = 0
    countries_processed = 0
    countries_skipped = 0
    requests_used = 0

    checkpoints = db.query(StateSyncCheckpoint).all()
    checkpoint_map = {checkpoint.country_new_id: checkpoint for checkpoint in checkpoints}

    for country in countries:
        if requests_used >= request_limit:
            break

        checkpoint = checkpoint_map.get(country.id)
        if checkpoint is not None and checkpoint.sync_status == "success":
            countries_skipped += 1
            continue

        iso = (country.iso2 or "").strip().upper()
        if not iso:
            failures.append(StateSyncFailure(country_iso="", reason=f"Missing ISO for country id {country.id}"))
            continue

        now = datetime.now(timezone.utc)
        if checkpoint is None:
            checkpoint = StateSyncCheckpoint(
                country_new_id=country.id,
                iso2=iso,
                sync_status="pending",
                attempt_count=0,
            )
            db.add(checkpoint)
            checkpoint_map[country.id] = checkpoint

        checkpoint.iso2 = iso
        checkpoint.attempt_count = (checkpoint.attempt_count or 0) + 1
        checkpoint.last_attempt_at = now

        try:
            response = requests.get(
                f"https://api.countrystatecity.in/v1/countries/{iso}/states",
                headers={"X-CSCAPI-KEY": api_key},
                timeout=30,
            )
            response.raise_for_status()
            states_payload = response.json()
            requests_used += 1
        except (requests.RequestException, ValueError) as exc:
            checkpoint.sync_status = "failed"
            checkpoint.last_error = str(exc)[:500]
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()
            failures.append(StateSyncFailure(country_iso=iso, reason=str(exc)))
            continue

        if not isinstance(states_payload, list):
            checkpoint.sync_status = "failed"
            checkpoint.last_error = "Unexpected API response format."
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()
            failures.append(StateSyncFailure(country_iso=iso, reason="Unexpected API response format."))
            continue

        try:
            for state_item in states_payload:
                if not isinstance(state_item, dict):
                    continue

                state_name = str(state_item.get("name", "")).strip()
                state_code = state_item.get("iso2")
                state_code = str(state_code).strip().upper() if state_code is not None else None

                if not state_name:
                    continue

                existing_state = (
                    db.query(State)
                    .filter(
                        State.country_id == country.id,
                        State.state_name == state_name,
                    )
                    .first()
                )

                if existing_state is None and state_code:
                    existing_state = (
                        db.query(State)
                        .filter(
                            State.country_id == country.id,
                            State.state_code == state_code,
                        )
                        .first()
                    )

                if existing_state is None:
                    db.add(
                        State(
                            country_id=country.id,
                            state_name=state_name,
                            state_code=state_code,
                            is_active=True,
                        )
                    )
                    states_inserted += 1
                    continue

                has_changes = False
                if existing_state.state_name != state_name:
                    existing_state.state_name = state_name
                    has_changes = True
                if existing_state.state_code != state_code:
                    existing_state.state_code = state_code
                    has_changes = True
                if existing_state.is_active is not True:
                    existing_state.is_active = True
                    has_changes = True

                if has_changes:
                    states_updated += 1

            checkpoint.sync_status = "success"
            checkpoint.last_error = None
            checkpoint.last_success_at = datetime.now(timezone.utc)
            db.commit()
            countries_processed += 1
        except SQLAlchemyError as exc:
            db.rollback()

            checkpoint_retry = db.query(StateSyncCheckpoint).filter(StateSyncCheckpoint.country_new_id == country.id).first()
            if checkpoint_retry is None:
                checkpoint_retry = StateSyncCheckpoint(
                    country_new_id=country.id,
                    iso2=iso,
                    sync_status="failed",
                    attempt_count=1,
                    last_attempt_at=now,
                )
                db.add(checkpoint_retry)
            checkpoint_retry.sync_status = "failed"
            checkpoint_retry.last_error = f"DB error: {exc}"[:500]
            checkpoint_retry.last_attempt_at = datetime.now(timezone.utc)
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()

            failures.append(StateSyncFailure(country_iso=iso, reason=f"DB error: {exc}"))

    return SyncStatesResponse(
        message="States sync completed (incremental mode).",
        countries_processed=countries_processed,
        countries_failed=len(failures),
        countries_skipped=countries_skipped,
        requests_used=requests_used,
        request_limit=request_limit,
        states_inserted=states_inserted,
        states_updated=states_updated,
        failures=failures,
    )