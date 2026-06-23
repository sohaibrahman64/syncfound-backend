from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base, ensure_db_connection
from app.routes.country_route import router as country_router
from app.routes.auth_route import router as auth_router
from app.routes.matching_purpose_route import router as matching_purpose_router
from app.routes.user_role_route import router as user_role_router
from app.routes.cofounder_role_route import router as cofounder_role_router
from app.routes.user_skill_route import router as user_skill_router
from app.routes.cofounder_skill_route import router as cofounder_skill_router
from app.routes.location_preference_route import router as location_preference_router
from app.routes.primary_role_route import router as primary_role_router
from app.routes.secondary_role_route import router as secondary_role_router
from app.routes.funding_stage_route import router as funding_stage_router
from app.routes.time_commitment_route import router as time_commitment_router
from app.routes.risk_appetite_route import router as risk_appetite_router
from app.routes.industry_route import router as industry_router
from app.routes.employment_type_route import router as employment_type_router
from app.routes.location_type_route import router as location_type_router
from app.routes.linkedin_profile_route import router as linkedin_profile_router
from app.routes.image_upload_route import router as image_upload_router
from app.routes.user_profile_route import router as user_profile_router
from app.routes.matches_route import router as matches_router
from app.routes.monetization_route import router as monetization_router
from app.services.firebase_service import initialize_firebase
from app.services.apify_service import initialize_apify
from app.services.storage_service import initialize_storage, is_local_storage_enabled, get_local_upload_dir
import app.models.user_model  # noqa: F401
import app.models.country_new_model  # noqa: F401
import app.models.state_model  # noqa: F401
import app.models.state_sync_checkpoint_model  # noqa: F401
import app.models.matching_purpose_model  # noqa: F401
import app.models.user_role_model  # noqa: F401
import app.models.user_skill_model  # noqa: F401
import app.models.cofounder_skill_model  # noqa: F401
import app.models.location_preference_model  # noqa: F401
import app.models.primary_role_model  # noqa: F401
import app.models.secondary_role_model  # noqa: F401
import app.models.funding_stage_model  # noqa: F401
import app.models.time_commitment_model  # noqa: F401
import app.models.risk_appetite_model  # noqa: F401
import app.models.industry_model  # noqa: F401
import app.models.employment_type_model  # noqa: F401
import app.models.location_type_model  # noqa: F401
import app.models.linkedin_profile_model  # noqa: F401
import app.models.user_profile_model  # noqa: F401
import app.models.match_model  # noqa: F401
import app.models.match_connection_message_model  # noqa: F401
import app.models.monetization_model  # noqa: F401
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

if is_local_storage_enabled():
    local_upload_dir = get_local_upload_dir()
    local_upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(local_upload_dir)), name="uploads")

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(country_router)
app.include_router(auth_router)
app.include_router(matching_purpose_router)
app.include_router(user_role_router)
app.include_router(cofounder_role_router)
app.include_router(user_skill_router)
app.include_router(cofounder_skill_router)
app.include_router(location_preference_router)
app.include_router(primary_role_router)
app.include_router(secondary_role_router)
app.include_router(funding_stage_router)
app.include_router(time_commitment_router)
app.include_router(risk_appetite_router)
app.include_router(industry_router)
app.include_router(employment_type_router)
app.include_router(location_type_router)
app.include_router(linkedin_profile_router)
app.include_router(image_upload_router)
app.include_router(user_profile_router)
app.include_router(matches_router)
app.include_router(monetization_router)


@app.on_event("startup")
def startup_db() -> None:
    try:
        initialize_firebase()
        initialize_apify()
        initialize_storage()
        ensure_db_connection()
        Base.metadata.create_all(bind=engine)
    except RuntimeError as exc:
        logger.error(str(exc))

@app.get("/")
def root():
    return {"message": "Welcome to the Syncfound Backend API!"}