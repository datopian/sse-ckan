-- ============================================================================
-- Update Alembic Version to Migration 105
-- Sets the database migration version to the latest applied migration
-- ============================================================================

-- Create the alembic_version table if it doesn't exist
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Check current Alembic version
SELECT
    'Current Alembic version: ' || COALESCE(version_num, 'NOT SET') as status
FROM alembic_version
UNION ALL
SELECT 'Table was just created - no version set yet' as status
WHERE NOT EXISTS (SELECT 1 FROM alembic_version);

-- Delete any existing version (Alembic only stores one version at a time)
DELETE FROM alembic_version;

-- Insert the current migration version (105: 4a5e3465beb6)
INSERT INTO alembic_version (version_num)
VALUES ('4a5e3465beb6');

-- Verify the update
SELECT
    'Updated Alembic version: ' || version_num ||
    CASE
        WHEN version_num = '4a5e3465beb6' THEN ' ✓ SUCCESS'
        ELSE ' ✗ FAILED'
    END as status,
    'Migration 105 (autogenerate sync)' as migration_name
FROM alembic_version;

-- ============================================================================
-- Migration history for reference:
-- ============================================================================
-- 086: 19663581b3bb - Drop openid column
-- 087: ff1b303cab77 - Remove old authorization tables
-- 088: 3537d5420e0e - Delete extras which are deleted state
-- 089: 23c92480926e - Package activity migration check
-- 090: 980dcd44de4b - Delete migrate_version table
-- 091: 0ffc0b277141 - Group_extra group_id index
-- 092: 01afcadbd8c0 - Resource package_id index
-- 093: d4d9be9189fe - Remove activity.revision_id
-- 094: 588d7cfb9a41 - Add metadata_modified to resource table
-- 095: 9fadda785b07 - Drop continuity_id constraints
-- 096: 19ddad52b500 - Add plugin_extras to user table
-- 097: f789f233226e - Add package_member table
-- 098: ddbd0a9a4489 - Add image_url field to user table
-- 099: 3ae4b17ed66d - Create ApiToken table
-- 100: ccd38ad5fced - Remove package_tag_revision foreign keys
-- 101: d111f446733b - Add last_active column in user table
-- 102: ff13667243ed - Create conditional index on user
-- 103: 353aaf2701f0 - Add plugin_data to package table
-- 104: 9f33a0280c51 - Resource_view resource_id index
-- 105: 4a5e3465beb6 - Autogenerate sync (CURRENT)
-- ============================================================================
