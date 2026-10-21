-- Columns needed by PATCH /api/v1/users/me/profile/edit.
-- Apply this once before deploying the endpoint; existing tables are not altered by create_all().
ALTER TABLE user_profile
    ADD COLUMN IF NOT EXISTS years_of_experience INTEGER;

ALTER TABLE user_profile_compensation
    ADD COLUMN IF NOT EXISTS expected_minimum_salary_id BIGINT;

ALTER TABLE user_profile_compensation
    DROP CONSTRAINT IF EXISTS fk_expected_minimum_salary_id;

ALTER TABLE user_profile_compensation
    ADD CONSTRAINT fk_expected_minimum_salary_id
    FOREIGN KEY (expected_minimum_salary_id) REFERENCES expected_minimum_salary(id);

ALTER TABLE user_job_search_profile
    ADD COLUMN IF NOT EXISTS user_profile_id BIGINT REFERENCES user_profile(id) ON DELETE CASCADE;

ALTER TABLE user_job_search_profile
    ADD COLUMN IF NOT EXISTS founders_can_see BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE linkedin_profile_education
    ADD COLUMN IF NOT EXISTS description TEXT;

-- The supplied schema names the target singular in the FK but creates the plural table.
ALTER TABLE user_profile_edit
    DROP CONSTRAINT IF EXISTS fk_user_profile_matching_goal_id;

ALTER TABLE user_profile_edit
    ADD CONSTRAINT fk_user_profile_matching_goal_id
    FOREIGN KEY (user_profile_matching_goal_id)
    REFERENCES user_profile_matching_goals(id)
    ON DELETE CASCADE;

-- Founder-only and talent-only profiles do not need references to the other branch.
ALTER TABLE user_profile_edit
    ALTER COLUMN user_profile_matching_goal_id DROP NOT NULL,
    ALTER COLUMN user_profile_commitment_level_id DROP NOT NULL,
    ALTER COLUMN user_profile_equity_split_id DROP NOT NULL,
    ALTER COLUMN user_profile_no_of_founders DROP NOT NULL,
    ALTER COLUMN user_job_search_profile_id DROP NOT NULL,
    ALTER COLUMN user_profile_compensation_id DROP NOT NULL,
    ALTER COLUMN user_profile_company_size_id DROP NOT NULL;
