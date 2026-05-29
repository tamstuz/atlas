# Production Harness Read First

The production harness defines the rules that AI Lab agents must follow while handling project work. It is the stable behavior contract for workflow state, role boundaries, runtime control, and verification.

Agents must not edit `harness/prod` directly. Proposed changes belong in `harness/candidate` and require review before promotion.

Agents load only the role and workflow rules needed for their assigned work. All runtime paths used by agents must be absolute paths.
