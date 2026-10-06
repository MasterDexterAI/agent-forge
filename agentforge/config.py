from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    llm_mode: str = "live"
    fake_llm_dir: str = "tests/fixtures/fake_llm"
    planner_model: str = "gemini/gemini-2.5-flash"
    tester_model: str = "gemini/gemini-2.5-flash"
    coder_model: str = "gemini/gemini-2.5-flash"
    reviewer_model: str = "groq/llama-3.3-70b-versatile"
    fallback_models: list[str] = ["groq/llama-3.3-70b-versatile"]
    langfuse_enabled: bool = False

    max_iterations: int = 3
    max_replans: int = 1
    review_threshold: float = 0.7
    run_budget_usd: float = 0.50
    max_tokens_per_run: int = 400_000
    max_prompt_chars: int = 4000

    sandbox_image: str = "agentforge-sandbox:latest"
    sandbox_runtime: str = "runsc"
    sandbox_timeout_s: int = 60
    sandbox_mem: str = "512m"
    max_concurrent_sandboxes: int = 2
    workspace_root: str = "/srv/agentforge/workspaces"

    internal_api_key: str
    stream_token_secret: str
    frontend_origin: str = "http://localhost:3000"
    runs_per_user_per_day: int = 5
    accept_new_runs: bool = True


settings = Settings()
