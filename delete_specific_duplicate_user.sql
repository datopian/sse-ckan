-- ============================================================================
-- Delete Specific Duplicate User
-- Deletes: anne-laube (less active duplicate)
-- Keeps: anne_laube (more active original)
-- ============================================================================

-- Show the user that will be deleted
SELECT
    'User to be deleted:' as action,
    id,
    name,
    email,
    created,
    last_active,
    (SELECT COUNT(*) FROM activity WHERE user_id = '6a31ae47-2001-4585-af3c-d0b951ecec0c') as activities
FROM "user"
WHERE id = '6a31ae47-2001-4585-af3c-d0b951ecec0c';

-- Mark the duplicate user as deleted
UPDATE "user"
SET state = 'deleted'
WHERE id = '6a31ae47-2001-4585-af3c-d0b951ecec0c'
  AND email = 'anne.laube@bag.admin.ch';

-- Verify the update
SELECT
    'Deletion result: ' ||
    CASE
        WHEN state = 'deleted' THEN 'SUCCESS ✓'
        ELSE 'FAILED ✗'
    END as status,
    id,
    name,
    email,
    state
FROM "user"
WHERE id = '6a31ae47-2001-4585-af3c-d0b951ecec0c';

-- Verify no duplicate active emails remain
SELECT
    'Duplicate check: ' ||
    CASE
        WHEN COUNT(*) = 0 THEN 'SUCCESS - No duplicates ✓'
        ELSE 'FAILED - Still ' || COUNT(*) || ' duplicates ✗'
    END as status
FROM (
    SELECT email
    FROM "user"
    WHERE state = 'active'
    GROUP BY email
    HAVING COUNT(*) > 1
) duplicates;

-- ============================================================================
-- Done! Now you can run apply_missing_constraints.sql
-- ============================================================================
