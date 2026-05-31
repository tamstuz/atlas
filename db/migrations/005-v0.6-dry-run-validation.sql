ALTER TABLE approvals ADD COLUMN IF NOT EXISTS validation_status TEXT;
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS validation_artifact_path TEXT;
