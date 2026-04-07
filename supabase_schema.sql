-- Run this in Supabase SQL editor.

create extension if not exists pgcrypto;

create table if not exists public.chat_sessions (
  id uuid primary key default gen_random_uuid(),
  title text not null default 'New chat',
  created_at timestamptz not null default now(),
  last_message_at timestamptz not null default now()
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_chat_messages_session_created
  on public.chat_messages (session_id, created_at);

create index if not exists idx_chat_sessions_last_message
  on public.chat_sessions (last_message_at desc);

alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;

-- Example permissive policy for development only. Tighten for production.
create policy if not exists "Allow read sessions" on public.chat_sessions
for select using (true);

create policy if not exists "Allow write sessions" on public.chat_sessions
for insert with check (true);

create policy if not exists "Allow update sessions" on public.chat_sessions
for update using (true);

create policy if not exists "Allow read messages" on public.chat_messages
for select using (true);

create policy if not exists "Allow write messages" on public.chat_messages
for insert with check (true);

create table if not exists public.escalated_conversations (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  question text not null,
  chat_history jsonb not null default '[]'::jsonb,
  escalation_reason text,
  created_at timestamptz not null default now()
);

alter table public.escalated_conversations enable row level security;

create policy if not exists "Allow read escalated" on public.escalated_conversations
for select using (true);

create policy if not exists "Allow write escalated" on public.escalated_conversations
for insert with check (true);
