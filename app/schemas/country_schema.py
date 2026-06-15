from pydantic import BaseModel

class CountryResponse(BaseModel):
    id: int
    country_name: str
    country_code: str
    country_iso: str
    country_flag_path: str | None = None

    class Config:
        from_attributes = True


class CountryNewResponse(BaseModel):
    id: int
    country_name: str
    iso2: str
    iso3: str | None = None
    phone_code: str | None = None
    capital: str | None = None
    currency: str | None = None
    native_name: str | None = None
    emoji: str | None = None
    emoji_u: str | None = None
    country_flag_path: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class StateLookupByCountryCodeRequest(BaseModel):
    iso3: str
    phone_code: str


class StateLookupItemResponse(BaseModel):
    id: int
    state_name: str
    state_code: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class StateLookupByCountryCodeResponse(BaseModel):
    country_id: int
    country_name: str
    iso2: str
    iso3: str | None = None
    phone_code: str | None = None
    states: list[StateLookupItemResponse]


class CityLookupItemResponse(BaseModel):
    id: int
    city_name: str
    is_active: bool

    class Config:
        from_attributes = True


class CityLookupByCountryCodeResponse(BaseModel):
    country_id: int
    country_name: str
    iso2: str
    iso3: str | None = None
    phone_code: str | None = None
    cities: list[CityLookupItemResponse]


class StateSyncFailure(BaseModel):
    country_iso: str
    reason: str


class SyncStatesResponse(BaseModel):
    message: str
    countries_processed: int
    countries_failed: int
    countries_skipped: int = 0
    requests_used: int = 0
    request_limit: int = 0
    states_inserted: int
    states_updated: int
    failures: list[StateSyncFailure] = []


class CountrySyncFailure(BaseModel):
    identifier: str
    reason: str


class SyncCountriesNewResponse(BaseModel):
    message: str
    countries_inserted: int
    countries_updated: int
    countries_failed: int
    failures: list[CountrySyncFailure] = []


class FlagDownloadFailure(BaseModel):
    iso2: str
    reason: str


class DownloadCountryFlagsResponse(BaseModel):
    message: str
    countries_processed: int
    flags_downloaded: int
    countries_failed: int
    destination_path: str
    failures: list[FlagDownloadFailure] = []


class BackfillStateCheckpointsResponse(BaseModel):
    message: str
    countries_scanned: int
    countries_with_states: int
    countries_without_states: int
    checkpoints_created: int
    checkpoints_updated: int


class CitySyncFailure(BaseModel):
    country_iso: str
    reason: str


class SyncCitiesResponse(BaseModel):
    message: str
    countries_processed: int
    countries_failed: int
    countries_skipped: int = 0
    cities_inserted: int
    cities_updated: int
    failures: list[CitySyncFailure] = []