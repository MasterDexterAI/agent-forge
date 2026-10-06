create table if not exists runs (
    id uuid primary key,
    user_id text not null,
    prompt text not null,
    status text not null default 'queued',
    idempotency_key text,
    cost_usd numeric(10, 4) not null default 0,
    tokens_used integer not null default 0,
    iterations integer not null default 0,
    is_public boolean not null default false,
    result jsonb,
    error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id, idempotency_key)
);

create index if not exists runs_user_created on runs (user_id, created_at desc);
create index if not exists runs_status on runs (status);

create table if not exists audit_log (
    id bigserial primary key,
    run_id uuid,
    actor text not null,
    action text not null,
    detail jsonb,
    created_at timestamptz not null default now()
);

create index if not exists audit_run on audit_log (run_id);

create table if not exists eval_results (
    id bigserial primary key,
    suite text not null,
    git_sha text,
    prompt_version text,
    models jsonb,
    summary jsonb not null,
    created_at timestamptz not null default now()
);
