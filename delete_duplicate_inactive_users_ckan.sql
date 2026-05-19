-- ============================================================================
-- Delete Less-Used Duplicate Users - CKAN Specific
-- Analyzes CKAN-specific user activity to determine which duplicate to keep
-- ============================================================================

-- Step 1: Comprehensive CKAN User Activity Analysis
WITH duplicate_emails AS (
    -- Find all duplicate active emails
    SELECT email
    FROM "user"
    WHERE state = 'active'
    GROUP BY email
    HAVING COUNT(*) > 1
),
user_ckan_activity AS (
    SELECT
        u.id,
        u.name,
        u.email,
        u.created,
        u.last_active,
        u.sysadmin,
        u.fullname,

        -- CKAN Activity Metrics
        -- 1. Datasets/Packages created
        (SELECT COUNT(*)
         FROM package p
         WHERE p.creator_user_id = u.id
         AND p.state = 'active') as datasets_created,

        -- 2. Organization/Group memberships (as admin, editor, or member)
        (SELECT COUNT(*)
         FROM member m
         WHERE m.table_id = u.id
         AND m.table_name = 'user'
         AND m.state = 'active') as org_memberships,

        -- 3. Admin roles in organizations
        (SELECT COUNT(*)
         FROM member m
         WHERE m.table_id = u.id
         AND m.table_name = 'user'
         AND m.capacity = 'admin'
         AND m.state = 'active') as admin_roles,

        -- 4. Package memberships
        (SELECT COUNT(*)
         FROM package_member pm
         WHERE pm.user_id = u.id) as package_memberships,

        -- 5. Activities performed
        (SELECT COUNT(*)
         FROM activity a
         WHERE a.user_id = u.id) as activities_count,

        -- 6. API tokens
        (SELECT COUNT(*)
         FROM api_token at
         WHERE at.user_id = u.id) as api_tokens,

        -- 7. Following datasets
        (SELECT COUNT(*)
         FROM user_following_dataset ufd
         WHERE ufd.follower_id = u.id) as following_datasets,

        -- 8. Following groups/orgs
        (SELECT COUNT(*)
         FROM user_following_group ufg
         WHERE ufg.follower_id = u.id) as following_groups,

        -- 9. Followers (users following this user)
        (SELECT COUNT(*)
         FROM user_following_user ufu
         WHERE ufu.object_id = u.id) as followers_count,

        -- 10. Most recent activity timestamp
        (SELECT MAX(a.timestamp)
         FROM activity a
         WHERE a.user_id = u.id) as last_activity_timestamp,

        -- Calculate comprehensive activity score
        CASE WHEN u.sysadmin THEN 100000 ELSE 0 END + -- Sysadmins always kept
        CASE WHEN u.last_active IS NOT NULL THEN 10000 ELSE 0 END + -- Has logged in recently
        (SELECT COUNT(*) FROM package WHERE creator_user_id = u.id AND state = 'active') * 1000 + -- Datasets
        (SELECT COUNT(*) FROM member WHERE table_id = u.id AND table_name = 'user' AND capacity = 'admin' AND state = 'active') * 500 + -- Admin roles
        (SELECT COUNT(*) FROM member WHERE table_id = u.id AND table_name = 'user' AND state = 'active') * 100 + -- Org memberships
        (SELECT COUNT(*) FROM package_member WHERE user_id = u.id) * 200 + -- Package memberships
        (SELECT COUNT(*) FROM activity WHERE user_id = u.id) * 10 + -- Activities
        (SELECT COUNT(*) FROM api_token WHERE user_id = u.id) * 50 + -- API tokens
        (SELECT COUNT(*) FROM user_following_dataset WHERE follower_id = u.id) * 5 + -- Following
        (SELECT COUNT(*) FROM user_following_user WHERE object_id = u.id) * 20 -- Being followed
        as activity_score

    FROM "user" u
    WHERE u.email IN (SELECT email FROM duplicate_emails)
      AND u.state = 'active'
)
SELECT
    email,
    id,
    name,
    fullname,
    created,
    last_active,
    last_activity_timestamp,
    sysadmin,
    datasets_created,
    org_memberships,
    admin_roles,
    package_memberships,
    activities_count,
    api_tokens,
    following_datasets,
    following_groups,
    followers_count,
    activity_score,
    ROW_NUMBER() OVER (
        PARTITION BY email
        ORDER BY
            activity_score DESC,
            last_active DESC NULLS LAST,
            last_activity_timestamp DESC NULLS LAST,
            created DESC
    ) as rank,
    CASE
        WHEN ROW_NUMBER() OVER (
            PARTITION BY email
            ORDER BY
                activity_score DESC,
                last_active DESC NULLS LAST,
                last_activity_timestamp DESC NULLS LAST,
                created DESC
        ) = 1 THEN '✓ KEEP'
        ELSE '✗ DELETE'
    END as action
FROM user_ckan_activity
ORDER BY email, activity_score DESC;

-- ============================================================================
-- Step 2: Summary of users that will be DELETED
-- ============================================================================
\echo ''
\echo '=========================================='
\echo 'USERS THAT WILL BE DELETED:'
\echo '=========================================='

WITH duplicate_emails AS (
    SELECT email
    FROM "user"
    WHERE state = 'active'
    GROUP BY email
    HAVING COUNT(*) > 1
),
user_ckan_activity AS (
    SELECT
        u.id,
        u.name,
        u.email,
        u.created,
        u.last_active,
        u.sysadmin,
        u.fullname,
        CASE WHEN u.sysadmin THEN 100000 ELSE 0 END +
        CASE WHEN u.last_active IS NOT NULL THEN 10000 ELSE 0 END +
        (SELECT COUNT(*) FROM package WHERE creator_user_id = u.id AND state = 'active') * 1000 +
        (SELECT COUNT(*) FROM member WHERE table_id = u.id AND table_name = 'user' AND capacity = 'admin' AND state = 'active') * 500 +
        (SELECT COUNT(*) FROM member WHERE table_id = u.id AND table_name = 'user' AND state = 'active') * 100 +
        (SELECT COUNT(*) FROM package_member WHERE user_id = u.id) * 200 +
        (SELECT COUNT(*) FROM activity WHERE user_id = u.id) * 10 +
        (SELECT COUNT(*) FROM api_token WHERE user_id = u.id) * 50 +
        (SELECT COUNT(*) FROM user_following_dataset WHERE follower_id = u.id) * 5 +
        (SELECT COUNT(*) FROM user_following_user WHERE object_id = u.id) * 20
        as activity_score,
        (SELECT MAX(a.timestamp) FROM activity a WHERE a.user_id = u.id) as last_activity_timestamp
    FROM "user" u
    WHERE u.email IN (SELECT email FROM duplicate_emails)
      AND u.state = 'active'
),
ranked_users AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY email
            ORDER BY
                activity_score DESC,
                last_active DESC NULLS LAST,
                last_activity_timestamp DESC NULLS LAST,
                created DESC
        ) as rank
    FROM user_ckan_activity
)
SELECT
    email,
    id,
    name,
    fullname,
    created,
    last_active,
    sysadmin,
    activity_score
FROM ranked_users
WHERE rank > 1
ORDER BY email;

-- ============================================================================
-- Step 3: DELETE less-active duplicate users
-- UNCOMMENT THE SECTION BELOW TO EXECUTE THE DELETE
-- ============================================================================

-- \echo ''
-- \echo '=========================================='
-- \echo 'DELETING INACTIVE DUPLICATE USERS...'
-- \echo '=========================================='

-- WITH duplicate_emails AS (
--     SELECT email
--     FROM "user"
--     WHERE state = 'active'
--     GROUP BY email
--     HAVING COUNT(*) > 1
-- ),
-- user_ckan_activity AS (
--     SELECT
--         u.id,
--         u.email,
--         u.last_active,
--         u.created,
--         CASE WHEN u.sysadmin THEN 100000 ELSE 0 END +
--         CASE WHEN u.last_active IS NOT NULL THEN 10000 ELSE 0 END +
--         (SELECT COUNT(*) FROM package WHERE creator_user_id = u.id AND state = 'active') * 1000 +
--         (SELECT COUNT(*) FROM member WHERE table_id = u.id AND table_name = 'user' AND capacity = 'admin' AND state = 'active') * 500 +
--         (SELECT COUNT(*) FROM member WHERE table_id = u.id AND table_name = 'user' AND state = 'active') * 100 +
--         (SELECT COUNT(*) FROM package_member WHERE user_id = u.id) * 200 +
--         (SELECT COUNT(*) FROM activity WHERE user_id = u.id) * 10 +
--         (SELECT COUNT(*) FROM api_token WHERE user_id = u.id) * 50 +
--         (SELECT COUNT(*) FROM user_following_dataset WHERE follower_id = u.id) * 5 +
--         (SELECT COUNT(*) FROM user_following_user WHERE object_id = u.id) * 20
--         as activity_score,
--         (SELECT MAX(a.timestamp) FROM activity a WHERE a.user_id = u.id) as last_activity_timestamp
--     FROM "user" u
--     WHERE u.email IN (SELECT email FROM duplicate_emails)
--       AND u.state = 'active'
-- ),
-- ranked_users AS (
--     SELECT
--         id,
--         ROW_NUMBER() OVER (
--             PARTITION BY email
--             ORDER BY
--                 activity_score DESC,
--                 last_active DESC NULLS LAST,
--                 last_activity_timestamp DESC NULLS LAST,
--                 created DESC
--         ) as rank
--     FROM user_ckan_activity
-- )
-- UPDATE "user"
-- SET state = 'deleted'
-- WHERE id IN (SELECT id FROM ranked_users WHERE rank > 1);

-- \echo 'Done! Duplicate inactive users have been marked as deleted.'

-- ============================================================================
-- Step 4: Verification
-- ============================================================================

-- \echo ''
-- \echo '=========================================='
-- \echo 'VERIFICATION: Checking for remaining duplicates'
-- \echo '=========================================='

-- SELECT
--     CASE
--         WHEN COUNT(*) = 0 THEN 'SUCCESS: No duplicate active emails remain'
--         ELSE 'WARNING: ' || COUNT(*) || ' duplicate emails still exist'
--     END as status
-- FROM (
--     SELECT email
--     FROM "user"
--     WHERE state = 'active'
--     GROUP BY email
--     HAVING COUNT(*) > 1
-- ) duplicates;

-- ============================================================================
-- Step 5: After cleanup, create the unique index
-- UNCOMMENT AFTER VERIFYING THE DELETE WORKED
-- ============================================================================

-- CREATE UNIQUE INDEX IF NOT EXISTS idx_only_one_active_email
--     ON "user"(email, state)
--     WHERE state='active';

-- \echo 'Unique index created successfully!'

