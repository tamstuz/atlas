ALTER TABLE approvals ADD COLUMN IF NOT EXISTS approval_type TEXT;
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS artifact_path TEXT;
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS requested_by TEXT;
UPDATE approvals SET approval_type = action WHERE approval_type IS NULL;
