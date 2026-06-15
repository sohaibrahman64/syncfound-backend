from apify_client import ApifyClient
import os

def initialize_apify() -> None:
    apify_token = os.getenv("APIFY_API_TOKEN")
    if not apify_token:
        raise RuntimeError("Apify API token is not configured. Set APIFY_API_TOKEN in environment variables.")
    global apify_client
    apify_client = ApifyClient(apify_token)

def fetch_linkedin_profile(username: str) -> dict:
    if not username:
        raise ValueError("Username must be provided.")

    try:
        run_input = {"username": username}
        linkedin_profile_detail_apify_actor = os.getenv("APIFY_ACTOR")
        if not linkedin_profile_detail_apify_actor:
            raise RuntimeError("Apify actor is not configured. Set APIFY_ACTOR in environment variables.")
        run = apify_client.actor(linkedin_profile_detail_apify_actor).call(run_input=run_input)
        if not run or not run.default_dataset_id:
            raise RuntimeError("Apify did not return a valid run or default dataset ID.")
        
        dataset_items = list(apify_client.dataset(run.default_dataset_id).iterate_items())
        if not dataset_items or len(dataset_items) == 0:
            raise RuntimeError("No items found in Apify dataset for the given username.")
        
        return dataset_items[0]
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch LinkedIn profile data: {str(exc)}") from exc