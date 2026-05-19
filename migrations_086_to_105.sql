-- ============================================================================
-- CKAN Database Migration SQL
-- From: Migration 086 (19663581b3bb) - Drop openid column
-- To: Migration 105 (4a5e3465beb6) - Autogenerate sync
-- ============================================================================
-- Generated from Alembic migration files
-- Execute this script on your PostgreSQL database to apply all migrations
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Migration 086: Drop openid column
-- Revision ID: 19663581b3bb
-- ----------------------------------------------------------------------------
ALTER TABLE "user" DROP COLUMN IF EXISTS openid;
DROP INDEX IF EXISTS idx_openid;

-- ----------------------------------------------------------------------------
-- Migration 087: Remove old authorization tables
-- Revision ID: ff1b303cab77
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS authorization_group_user;
DROP TABLE IF EXISTS authorization_group;

-- ----------------------------------------------------------------------------
-- Migration 088: Delete extras which are deleted state
-- Revision ID: 3537d5420e0e
-- ----------------------------------------------------------------------------
-- Drop foreign key constraints first
ALTER TABLE package_extra_revision
    DROP CONSTRAINT IF EXISTS package_extra_revision_continuity_id_fkey;

ALTER TABLE group_extra_revision
    DROP CONSTRAINT IF EXISTS group_extra_revision_continuity_id_fkey;

-- Delete records with deleted state
DELETE FROM package_extra WHERE state='deleted';
DELETE FROM group_extra WHERE state='deleted';

-- ----------------------------------------------------------------------------
-- Migration 089: Package activity migration check
-- Revision ID: 23c92480926e
-- Note: This migration only performs checks and prints messages
-- No SQL statements to execute
-- ----------------------------------------------------------------------------

-- ----------------------------------------------------------------------------
-- Migration 090: Delete migrate_version table
-- Revision ID: 980dcd44de4b
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS migrate_version;

-- ----------------------------------------------------------------------------
-- Migration 091: Group_extra group_id index
-- Revision ID: 0ffc0b277141
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_group_extra_group_id ON group_extra(group_id);

-- ----------------------------------------------------------------------------
-- Migration 092: Resource package_id index
-- Revision ID: 01afcadbd8c0
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_package_resource_package_id ON resource(package_id);

-- ----------------------------------------------------------------------------
-- Migration 093: Remove activity.revision_id
-- Revision ID: d4d9be9189fe
-- ----------------------------------------------------------------------------
-- Drop foreign key constraints and revision_id columns from multiple tables
ALTER TABLE "group" DROP CONSTRAINT IF EXISTS group_revision_id_fkey;
ALTER TABLE "group" DROP COLUMN IF EXISTS revision_id;

ALTER TABLE group_extra DROP CONSTRAINT IF EXISTS group_extra_revision_id_fkey;
ALTER TABLE group_extra DROP COLUMN IF EXISTS revision_id;

ALTER TABLE member DROP CONSTRAINT IF EXISTS member_revision_id_fkey;
ALTER TABLE member DROP COLUMN IF EXISTS revision_id;

ALTER TABLE package DROP CONSTRAINT IF EXISTS package_revision_id_fkey;
ALTER TABLE package DROP COLUMN IF EXISTS revision_id;

ALTER TABLE package_extra DROP CONSTRAINT IF EXISTS package_extra_revision_id_fkey;
ALTER TABLE package_extra DROP COLUMN IF EXISTS revision_id;

ALTER TABLE package_relationship DROP CONSTRAINT IF EXISTS package_relationship_revision_id_fkey;
ALTER TABLE package_relationship DROP COLUMN IF EXISTS revision_id;

ALTER TABLE package_tag DROP CONSTRAINT IF EXISTS package_tag_revision_id_fkey;
ALTER TABLE package_tag DROP COLUMN IF EXISTS revision_id;

ALTER TABLE resource DROP CONSTRAINT IF EXISTS resource_revision_id_fkey;
ALTER TABLE resource DROP COLUMN IF EXISTS revision_id;

ALTER TABLE system_info DROP CONSTRAINT IF EXISTS system_info_revision_id_fkey;
ALTER TABLE system_info DROP COLUMN IF EXISTS revision_id;

-- ----------------------------------------------------------------------------
-- Migration 094: Add metadata_modified field to Resource
-- Revision ID: 588d7cfb9a41
-- ----------------------------------------------------------------------------
ALTER TABLE resource ADD COLUMN IF NOT EXISTS metadata_modified TIMESTAMP;
UPDATE resource SET metadata_modified = created WHERE metadata_modified IS NULL;

-- ----------------------------------------------------------------------------
-- Migration 095: Drop continuity_id constraints
-- Revision ID: 9fadda785b07
-- ----------------------------------------------------------------------------
ALTER TABLE member_revision
    DROP CONSTRAINT IF EXISTS member_revision_continuity_id_fkey;

ALTER TABLE resource_revision
    DROP CONSTRAINT IF EXISTS resource_revision_continuity_id_fkey;

ALTER TABLE package_revision
    DROP CONSTRAINT IF EXISTS package_revision_continuity_id_fkey;

-- ----------------------------------------------------------------------------
-- Migration 096: Add plugin_extras to user table
-- Revision ID: 19ddad52b500
-- ----------------------------------------------------------------------------
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS plugin_extras JSONB;

-- ----------------------------------------------------------------------------
-- Migration 097: Add package_member table
-- Revision ID: f789f233226e
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS package_member (
    package_id TEXT,
    user_id TEXT,
    capacity TEXT NOT NULL,
    modified TIMESTAMP NOT NULL,
    CONSTRAINT package_member_pkey PRIMARY KEY (package_id, user_id),
    CONSTRAINT package_member_package_id_fkey FOREIGN KEY (package_id) REFERENCES package(id),
    CONSTRAINT package_member_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
);

-- ----------------------------------------------------------------------------
-- Migration 098: Add image_url field to user table
-- Revision ID: ddbd0a9a4489
-- ----------------------------------------------------------------------------
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS image_url TEXT;

-- ----------------------------------------------------------------------------
-- Migration 099: Create ApiToken table
-- Revision ID: 3ae4b17ed66d
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_token (
    id TEXT PRIMARY KEY,
    name TEXT,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_access TIMESTAMP,
    plugin_extras JSONB,
    CONSTRAINT api_token_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
);

-- ----------------------------------------------------------------------------
-- Migration 100: Remove package_tag_revision foreign keys
-- Revision ID: ccd38ad5fced
-- ----------------------------------------------------------------------------
ALTER TABLE package_tag_revision
    DROP CONSTRAINT IF EXISTS package_tag_revision_continuity_id_fkey;

ALTER TABLE package_tag_revision
    DROP CONSTRAINT IF EXISTS package_tag_revision_package_id_fkey;

ALTER TABLE package_extra_revision
    DROP CONSTRAINT IF EXISTS package_extra_revision_package_id_fkey;

ALTER TABLE group_revision
    DROP CONSTRAINT IF EXISTS group_revision_continuity_id_fkey;

ALTER TABLE member_revision
    DROP CONSTRAINT IF EXISTS member_revision_group_id_fkey;

-- ----------------------------------------------------------------------------
-- Migration 101: Add last_active column in user table
-- Revision ID: d111f446733b
-- ----------------------------------------------------------------------------
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS last_active TIMESTAMP;

-- ----------------------------------------------------------------------------
-- Migration 102: Create conditional index on user
-- Revision ID: ff13667243ed
-- ----------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS idx_only_one_active_email
    ON "user"(email, state)
    WHERE state='active';

-- ----------------------------------------------------------------------------
-- Migration 103: Add plugin_data to package table
-- Revision ID: 353aaf2701f0
-- ----------------------------------------------------------------------------
ALTER TABLE package ADD COLUMN IF NOT EXISTS plugin_data JSONB;

-- ----------------------------------------------------------------------------
-- Migration 104: Resource_view resource_id index
-- Revision ID: 9f33a0280c51
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_view_resource_id ON resource_view(resource_id);

-- ----------------------------------------------------------------------------
-- Migration 105: Autogenerate sync (cleanup and optimization)
-- Revision ID: 4a5e3465beb6
-- ----------------------------------------------------------------------------

-- Drop rating table and related indexes (removed feature)
DROP INDEX IF EXISTS idx_rating_id;
DROP INDEX IF EXISTS idx_rating_package_id;
DROP INDEX IF EXISTS idx_rating_user_id;
DROP TABLE IF EXISTS rating;

-- Enforce package/resource relationship
DO $$
DECLARE
    fk_exists boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname LIKE '%resource_package_id%'
        AND conrelid = 'resource'::regclass
        AND confrelid = 'package'::regclass
    ) INTO fk_exists;

    IF NOT fk_exists THEN
        ALTER TABLE resource ADD CONSTRAINT resource_package_id_fkey
            FOREIGN KEY (package_id) REFERENCES package(id);
    END IF;
END $$;

-- Drop long-forgotten columns from resource table
ALTER TABLE resource DROP COLUMN IF EXISTS webstore_last_updated;
ALTER TABLE resource DROP COLUMN IF EXISTS webstore_url;

-- Drop redundant indexes
DROP INDEX IF EXISTS idx_package_group_group_id;
DROP INDEX IF EXISTS idx_package_group_pkg_id;
DROP INDEX IF EXISTS idx_package_group_pkg_id_group_id;
DROP INDEX IF EXISTS idx_pkg_id;
DROP INDEX IF EXISTS idx_pkg_name;
DROP INDEX IF EXISTS idx_pkg_title;
DROP INDEX IF EXISTS idx_package_tag_tag_id;
DROP INDEX IF EXISTS term;

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- All migrations from 086 to 105 have been applied
-- Please verify the results and test your application
-- ============================================================================
