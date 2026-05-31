from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ai_lab_root: Path = Field(default=Path("/srv/ai-lab"), alias="AI_LAB_ROOT")
    ai_lab_host: str = Field(default="0.0.0.0", alias="AI_LAB_HOST")
    ai_lab_port: int = Field(default=8088, alias="AI_LAB_PORT")

    postgres_db: str = Field(default="ailab", alias="POSTGRES_DB")
    postgres_user: str = Field(default="ailab", alias="POSTGRES_USER")
    postgres_password: str = Field(default="change-me", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="127.0.0.1", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    qdrant_url: str = Field(default="http://127.0.0.1:6333", alias="QDRANT_URL")
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")
    ollama_enabled: bool = Field(default=True, alias="OLLAMA_ENABLED")
    ollama_base_url: str = Field(default="http://ollama.example.local:11434", alias="OLLAMA_BASE_URL")
    llm_timeout_seconds: float = Field(default=120.0, alias="LLM_TIMEOUT_SECONDS")
    ollama_timeout_seconds: float | None = Field(default=None, alias="OLLAMA_TIMEOUT_SECONDS")
    default_model: str = Field(default="gemma4:26b", alias="DEFAULT_MODEL")
    analyst_model: str | None = Field(default=None, alias="ANALYST_MODEL")
    architect_model: str | None = Field(default=None, alias="ARCHITECT_MODEL")
    developer_model: str | None = Field(default=None, alias="DEVELOPER_MODEL")
    qa_model: str | None = Field(default=None, alias="QA_MODEL")
    final_report_model: str | None = Field(default=None, alias="FINAL_REPORT_MODEL")
    runtime_inspection_commands_enabled: bool = Field(default=False, alias="RUNTIME_INSPECTION_COMMANDS_ENABLED")

    harness_dir: Path = Field(default=Path("/srv/ai-lab/harness/prod"), alias="HARNESS_DIR")
    skills_dir: Path = Field(default=Path("/srv/ai-lab/skills/prod"), alias="SKILLS_DIR")
    projects_dir: Path = Field(default=Path("/srv/ai-lab/projects"), alias="PROJECTS_DIR")
    runtime_dir: Path = Field(default=Path("/srv/ai-lab/runtime"), alias="RUNTIME_DIR")
    registry_dir: Path = Field(default=Path("/srv/ai-lab/runtime/registries"), alias="REGISTRY_DIR")
    log_dir: Path = Field(default=Path("/srv/ai-lab/runtime/logs"), alias="LOG_DIR")

    def model_for_role(self, role: str) -> str:
        role_models = {
            "analyst": self.analyst_model,
            "architect": self.architect_model,
            "developer": self.developer_model,
            "qa": self.qa_model,
            "final_report": self.final_report_model,
        }
        return role_models.get(role) or self.default_model

    def role_models(self) -> dict[str, str]:
        return {
            "analyst": self.model_for_role("analyst"),
            "architect": self.model_for_role("architect"),
            "developer": self.model_for_role("developer"),
            "qa": self.model_for_role("qa"),
            "final_report": self.model_for_role("final_report"),
        }

    @property
    def effective_llm_timeout_seconds(self) -> float:
        return self.ollama_timeout_seconds or self.llm_timeout_seconds

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def safe_config(self) -> dict[str, object]:
        return {
            "ai_lab_root": str(self.ai_lab_root),
            "ai_lab_host": self.ai_lab_host,
            "ai_lab_port": self.ai_lab_port,
            "postgres_host": self.postgres_host,
            "postgres_port": self.postgres_port,
            "postgres_db": self.postgres_db,
            "qdrant_url": self.qdrant_url,
            "llm_provider": self.llm_provider,
            "ollama_enabled": self.ollama_enabled,
            "ollama_base_url": self.ollama_base_url,
            "llm_timeout_seconds": self.effective_llm_timeout_seconds,
            "default_model": self.default_model,
            "role_models": self.role_models(),
            "runtime_inspection_commands_enabled": self.runtime_inspection_commands_enabled,
            "harness_dir": str(self.harness_dir),
            "skills_dir": str(self.skills_dir),
            "projects_dir": str(self.projects_dir),
            "runtime_dir": str(self.runtime_dir),
            "registry_dir": str(self.registry_dir),
            "log_dir": str(self.log_dir),
        }


settings = Settings()
