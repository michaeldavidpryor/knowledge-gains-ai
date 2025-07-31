"""
Supabase table suggestions (SQL):

-- Enable pgvector extension first
create extension if not exists vector;

create table wizard_answers (
  id uuid primary key,
  user_id uuid,
  answers jsonb
);

create table routines (
  id uuid primary key,
  user_id uuid,
  routine_json jsonb,
  created_at timestamptz
);

-- one row per completed set
create table progress_logs (
  id uuid primary key,
  user_id uuid,
  routine_id uuid,
  week int,
  day int,
  exercise_name text,
  set_number int,
  weight numeric,
  reps int,
  notes text,
  ts timestamptz
);

-- file upload storage with embeddings
create table file_vectors (
  id uuid primary key,
  user_id uuid,
  filename text,
  file_text text,
  embedding vector(1536),
  ts timestamptz
);

-- completed workout days
create table completed_days (
  id uuid primary key,
  user_id uuid,
  routine_id uuid,
  week int,
  day int,
  ts timestamptz
);
"""
