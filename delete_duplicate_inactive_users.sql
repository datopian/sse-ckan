-- ============================================================================
-- Delete Less-Used Duplicate Users
-- Keeps the most active user for each duplicate email
-- ============================================================================

-- Step 1: Analyze duplicate users to see which ones are more active
WITH duplicate_emails AS (
    SELECT email
    FROM "user"
    WHERE state = 'active'
    GROUP BY email
    HAVING COUNT(*) > 1
),
user_activity AS (
    SELECT
        u.id,
        u.name,
        u.email,
        u.created,
        u.last_active,
        u.sysadmin,
        -- Count packages created by user
        (SELECT COUNT(*) FROM package WHERE creator_user_id = u.id) as packages_created,
        -- Count activities by user
        (SELECT COUNT(*) FROM activity WHERE user_id = u.id) as activities_count,
        -- Count API tokens
        (SELECT COUNT(*) FROM api_token WHERE user_id = u.id) as api_tokens_count,
        -- Calculate activity score (higher = more active)
        CASE
            WHEN u.last_active IS NOT NULL THEN 1000
            ELSE 0
        END +
        (SELECT COUNT(*) FROM package WHERE creator_user_id = u.id) * 100 +
        (SELECT COUNT(*) FROM activity WHERE user_id = u.id) * 10 +
        CASE WHEN u.sysadmin THEN 10000 ELSE 0 END as activity_score
    FROM "user" u
    WHERE u.email IN (SELECT email FROM duplicate_emails)
      AND u.state = 'active'
)
SELECT
    email,
    id,
    name,
    created,
    last_active,
    sysadmin,
    packages_created,
    activities_count,
    api_tokens_count,
    activity_score,
    ROW_NUMBER() OVER (PARTITION BY email ORDER BY activity_score DESC, last_active DESC NULLS LAST, created DESC) as rank,
    CASE
        WHEN ROW_NUMBER() OVER (PARTITION BY email ORDER BY activity_score DESC, last_active DESC NULLS LAST, created DESC) = 1
        THEN 'KEEP'
        ELSE 'DELETE'
    END as action
FROM user_activity
ORDER BY email, activity_score DESC;

-- ============================================================================
-- Step 2: Preview users that will be DELETED (less active duplicates)
-- ============================================================================
WITH duplicate_emails AS (
    SELECT email
    FROM "user"
    WHERE state = 'active'
    GROUP BY email
    HAVING COUNT(*) > 1
),
user_activity AS (
    SELECT
        u.id,
        u.name,
        u.email,
        u.created,
        u.last_active,
        u.sysadmin,
        CASE
            WHEN u.last_active IS NOT NULL THEN 1000
            ELSE 0
        END +
        (SELECT COUNT(*) FROM package WHERE creator_user_id = u.id) * 100 +
        (SELECT COUNT(*) FROM activity WHERE user_id = u.id) * 10 +
        CASE WHEN u.sysadmin THEN 10000 ELSE 0 END as activity_score
    FROM "user" u
    WHERE u.email IN (SELECT email FROM duplicate_emails)
      AND u.state = 'active'
),
ranked_users AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY email ORDER BY activity_score DESC, last_active DESC NULLS LAST, created DESC) as rank
    FROM user_activity
)
SELECT
    'WILL BE DELETED:' as status,
    email,
    id,
    name,
    created,
    last_active,
    sysadmin
FROM ranked_users
WHERE rank > 1
ORDER BY email;

-- ============================================================================
-- Step 3: DELETE less-used duplicate users
-- UNCOMMENT BELOW TO EXECUTE THE DELETE
-- ============================================================================

-- WITH duplicate_emails AS (
--     SELECT email
--     FROM "user"
--     WHERE state = 'active'
--     GROUP BY email
--     HAVING COUNT(*) > 1
-- ),
-- user_activity AS (
--     SELECT
--         u.id,
--         u.email,
--         CASE
--             WHEN u.last_active IS NOT NULL THEN 1000
--             ELSE 0
--         END +
--         (SELECT COUNT(*) FROM package WHERE creator_user_id = u.id) * 100 +
--         (SELECT COUNT(*) FROM activity WHERE user_id = u.id) * 10 +
--         CASE WHEN u.sysadmin THEN 10000 ELSE 0 END as activity_score
--     FROM "user" u
--     WHERE u.email IN (SELECT email FROM duplicate_emails)
--       AND u.state = 'active'
-- ),
-- ranked_users AS (
--     SELECT
--         id,
--         email,
--         activity_score,
--         ROW_NUMBER() OVER (PARTITION BY email ORDER BY activity_score DESC, last_active DESC NULLS LAST, created DESC) as rank
--     FROM user_activity
-- )
-- UPDATE "user"
-- SET state = 'deleted'
-- WHERE id IN (
--     SELECT id
--     FROM ranked_users
--     WHERE rank > 1
-- );

-- ============================================================================
-- Alternative: More conservative approach - just mark as 'deleted' state
-- This is SAFER as it doesn't permanently delete data
-- UNCOMMENT BELOW TO EXECUTE
-- ============================================================================

-- WITH duplicate_emails AS (
--     SELECT email
--     FROM "user"
--     WHERE state = 'active'
--     GROUP BY email
--     HAVING COUNT(*) > 1
-- ),
-- user_activity AS (
--     SELECT
--         u.id,
--         u.email,
--         u.last_active,
--         u.created,
--         CASE
--             WHEN u.last_active IS NOT NULL THEN 1000
--             ELSE 0
--         END +
--         (SELECT COUNT(*) FROM package WHERE creator_user_id = u.id) * 100 +
--         (SELECT COUNT(*) FROM activity WHERE user_id = u.id) * 10 +
--         CASE WHEN u.sysadmin THEN 10000 ELSE 0 END as activity_score
--     FROM "user" u
--     WHERE u.email IN (SELECT email FROM duplicate_emails)
--       AND u.state = 'active'
-- ),
-- ranked_users AS (
--     SELECT
--         id,
--         ROW_NUMBER() OVER (PARTITION BY email ORDER BY activity_score DESC, last_active DESC NULLS LAST, created DESC) as rank
--     FROM user_activity
-- )
-- UPDATE "user"
-- SET state = 'deleted'
-- WHERE id IN (SELECT id FROM ranked_users WHERE rank > 1);

-- Verification: Check that no duplicate active emails remain
SELECT 'After cleanup - Duplicate check:' as status,
       COUNT(*) as remaining_duplicates
FROM (
    SELECT email
    FROM "user"
    WHERE state = 'active'
    GROUP BY email
    HAVING COUNT(*) > 1
) duplicates;

-- ============================================================================
-- Step 4: After fixing duplicates, create the unique index
-- UNCOMMENT AFTER RUNNING THE DELETE
-- ============================================================================
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_only_one_active_email
--     ON "user"(email, state)
--     WHERE state='active';

