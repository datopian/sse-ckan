-- ============================================================================
-- Apply Missing Constraints After Data Cleanup
-- Run this after fixing duplicate users and orphaned resources
-- ============================================================================

-- 1. Add the foreign key constraint for resource -> package
-- This ensures all resources reference valid packages
ALTER TABLE resource
ADD CONSTRAINT resource_package_id_fkey
FOREIGN KEY (package_id)
REFERENCES package(id);

-- 2. Create the unique index on user email (for active users only)
-- This ensures no duplicate active emails
CREATE UNIQUE INDEX idx_only_one_active_email
ON "user"(email, state)
WHERE state='active';

-- ============================================================================
-- Verification
-- ============================================================================

-- Verify the foreign key was created
SELECT
    'resource_package_id_fkey constraint: ' ||
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'resource_package_id_fkey'
        ) THEN 'CREATED ✓'
        ELSE 'FAILED ✗'
    END as status;

-- Verify the unique index was created
SELECT
    'idx_only_one_active_email index: ' ||
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'idx_only_one_active_email'
        ) THEN 'CREATED ✓'
        ELSE 'FAILED ✗'
    END as status;

-- Check for any remaining orphaned resources (should be 0)
SELECT
    'Orphaned resources: ' || COUNT(*)::text ||
    CASE
        WHEN COUNT(*) = 0 THEN ' ✓'
        ELSE ' ✗ WARNING: Still have orphaned resources!'
    END as status
FROM resource r
LEFT JOIN package p ON r.package_id = p.id
WHERE p.id IS NULL AND r.package_id IS NOT NULL;

-- Check for any remaining duplicate active emails (should be 0)
SELECT
    'Duplicate active emails: ' || COUNT(*)::text ||
    CASE
        WHEN COUNT(*) = 0 THEN ' ✓'
        ELSE ' ✗ WARNING: Still have duplicate emails!'
    END as status
FROM (
    SELECT email
    FROM "user"
    WHERE state = 'active'
    GROUP BY email
    HAVING COUNT(*) > 1
) duplicates;

-- ============================================================================
-- All constraints applied!
-- ============================================================================
