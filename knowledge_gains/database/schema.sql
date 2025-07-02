-- Knowledge Gains Database Schema for Supabase
-- Science-based weightlifting program tracking system

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (extends Supabase auth.users)
CREATE TABLE public.user_profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    display_name TEXT,
    email TEXT,
    fitness_level TEXT CHECK (fitness_level IN ('beginner', 'intermediate', 'advanced')),
    equipment_access TEXT NOT NULL, -- 'full_gym', 'home_gym', 'minimal', 'bodyweight'
    training_goals TEXT[], -- ['strength', 'hypertrophy', 'endurance', 'general_fitness']
    training_frequency INTEGER DEFAULT 3, -- days per week
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workout Programs table
CREATE TABLE public.workout_programs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    duration_weeks INTEGER NOT NULL,
    days_per_week INTEGER NOT NULL,
    equipment_required TEXT NOT NULL,
    difficulty_level TEXT CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    program_type TEXT, -- 'strength', 'hypertrophy', 'powerlifting', etc.
    
    -- AI Generation metadata
    generated_by_ai BOOLEAN DEFAULT TRUE,
    agent_version TEXT,
    source_files TEXT[], -- file hashes that influenced generation
    web_research_queries TEXT[], -- searches that influenced generation
    
    -- Program structure (JSON)
    program_data JSONB NOT NULL, -- Full program structure with weeks/workouts/exercises
    
    -- Status and tracking
    is_active BOOLEAN DEFAULT FALSE,
    start_date DATE,
    end_date DATE,
    completion_status TEXT DEFAULT 'not_started' CHECK (completion_status IN ('not_started', 'in_progress', 'completed', 'paused')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Individual Workouts (instances of program workouts)
CREATE TABLE public.workouts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    program_id UUID REFERENCES public.workout_programs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    
    -- Workout identification
    week_number INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    workout_name TEXT NOT NULL,
    workout_date DATE DEFAULT CURRENT_DATE,
    
    -- Workout status
    status TEXT DEFAULT 'planned' CHECK (status IN ('planned', 'in_progress', 'completed', 'skipped')),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    
    -- Workout data
    exercises JSONB NOT NULL, -- Exercise list with sets/reps/weights
    notes TEXT,
    perceived_exertion INTEGER CHECK (perceived_exertion BETWEEN 1 AND 10),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Exercise Database (reference exercises)
CREATE TABLE public.exercises (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL, -- 'compound', 'isolation', 'cardio'
    muscle_groups TEXT[] NOT NULL, -- ['chest', 'triceps', 'shoulders']
    equipment_required TEXT[], -- ['barbell', 'bench', 'rack']
    difficulty_level TEXT CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    
    -- Exercise details
    description TEXT,
    form_cues TEXT[],
    common_mistakes TEXT[],
    variations TEXT[],
    
    -- Progression information
    typical_rep_ranges JSONB, -- {'strength': '1-5', 'hypertrophy': '6-12', 'endurance': '12+'}
    progression_scheme TEXT, -- 'linear', 'percentage', 'RPE'
    
    -- Media and resources
    video_url TEXT,
    image_url TEXT,
    reference_links TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Exercise Sets (individual set tracking)
CREATE TABLE public.exercise_sets (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    workout_id UUID REFERENCES public.workouts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    exercise_id UUID REFERENCES public.exercises(id),
    
    -- Set identification
    exercise_name TEXT NOT NULL, -- Stored name in case exercise is deleted
    set_number INTEGER NOT NULL,
    
    -- Set data
    weight_kg DECIMAL(5,2), -- weight in kg (nullable for bodyweight exercises)
    reps_completed INTEGER,
    reps_planned INTEGER,
    rest_seconds INTEGER,
    
    -- Set quality metrics
    rpe INTEGER CHECK (rpe BETWEEN 1 AND 10), -- Rate of Perceived Exertion
    completed BOOLEAN DEFAULT FALSE,
    form_rating INTEGER CHECK (form_rating BETWEEN 1 AND 5), -- 1-5 form quality
    
    -- Progression tracking
    personal_record BOOLEAN DEFAULT FALSE,
    weight_increase_from_previous DECIMAL(5,2),
    
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Progression Tracking
CREATE TABLE public.progression_tracking (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    exercise_name TEXT NOT NULL,
    
    -- Progression metrics
    max_weight_kg DECIMAL(5,2),
    max_reps INTEGER,
    estimated_1rm DECIMAL(5,2),
    volume_progression DECIMAL(8,2), -- total volume (sets x reps x weight)
    
    -- Time tracking
    measurement_date DATE DEFAULT CURRENT_DATE,
    program_context TEXT, -- which program this was achieved in
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- File Uploads (user uploaded fitness documents)
CREATE TABLE public.uploaded_files (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    
    -- File information
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    file_type TEXT,
    file_hash TEXT UNIQUE, -- MD5 hash for deduplication
    
    -- Processing status
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    
    -- AI Analysis results
    analysis_results JSONB, -- Results from FileProcessorAgent
    programs_extracted INTEGER DEFAULT 0,
    exercises_identified INTEGER DEFAULT 0,
    
    -- Usage tracking
    used_in_programs UUID[], -- Array of program IDs that used this file
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Program Modifications (user requested changes)
CREATE TABLE public.program_modifications (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    program_id UUID REFERENCES public.workout_programs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    workout_id UUID REFERENCES public.workouts(id), -- specific workout modified (optional)
    
    -- Modification details
    modification_type TEXT NOT NULL, -- 'exercise_substitution', 'rep_adjustment', 'weight_adjustment', 'schedule_change'
    original_data JSONB NOT NULL, -- what was changed from
    modified_data JSONB NOT NULL, -- what it was changed to
    reason TEXT, -- user's reason for change
    
    -- AI involvement
    ai_suggested BOOLEAN DEFAULT FALSE,
    agent_reasoning TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Web Search History (for program research)
CREATE TABLE public.web_search_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    
    -- Search details
    search_query TEXT NOT NULL,
    search_type TEXT, -- 'program', 'exercise', 'research'
    
    -- Results
    results_summary JSONB, -- Analysis from FitnessWebAgent
    sources_found TEXT[],
    credibility_scores JSONB,
    
    -- Usage
    influenced_programs UUID[], -- Programs that used this research
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_user_profiles_email ON public.user_profiles(email);
CREATE INDEX idx_workout_programs_user_id ON public.workout_programs(user_id);
CREATE INDEX idx_workout_programs_active ON public.workout_programs(user_id, is_active);
CREATE INDEX idx_workouts_program_id ON public.workouts(program_id);
CREATE INDEX idx_workouts_user_date ON public.workouts(user_id, workout_date);
CREATE INDEX idx_exercise_sets_workout_id ON public.exercise_sets(workout_id);
CREATE INDEX idx_exercise_sets_user_exercise ON public.exercise_sets(user_id, exercise_name);
CREATE INDEX idx_progression_tracking_user_exercise ON public.progression_tracking(user_id, exercise_name);
CREATE INDEX idx_uploaded_files_user_id ON public.uploaded_files(user_id);
CREATE INDEX idx_uploaded_files_hash ON public.uploaded_files(file_hash);

-- Row Level Security (RLS) policies
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercise_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.progression_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uploaded_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.program_modifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.web_search_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies (users can only access their own data)
CREATE POLICY "Users can view own profile" ON public.user_profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.user_profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile" ON public.user_profiles FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can manage own programs" ON public.workout_programs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own workouts" ON public.workouts FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own sets" ON public.exercise_sets FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own progression" ON public.progression_tracking FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own files" ON public.uploaded_files FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own modifications" ON public.program_modifications FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own searches" ON public.web_search_history FOR ALL USING (auth.uid() = user_id);

-- Exercises table is public read, admin write
CREATE POLICY "Anyone can view exercises" ON public.exercises FOR SELECT USING (true);

-- Functions for common operations
CREATE OR REPLACE FUNCTION public.get_current_program(user_uuid UUID)
RETURNS TABLE(program_id UUID, program_name TEXT, current_week INTEGER, next_workout JSONB)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        wp.id,
        wp.name,
        COALESCE(
            (SELECT MAX(w.week_number) FROM public.workouts w 
             WHERE w.program_id = wp.id AND w.status = 'completed'), 
            0
        ) + 1 as current_week,
        (
            SELECT to_jsonb(w.*) FROM public.workouts w 
            WHERE w.program_id = wp.id 
            AND w.status = 'planned' 
            ORDER BY w.week_number, w.day_number 
            LIMIT 1
        ) as next_workout
    FROM public.workout_programs wp
    WHERE wp.user_id = user_uuid 
    AND wp.is_active = TRUE
    LIMIT 1;
END;
$$;

CREATE OR REPLACE FUNCTION public.calculate_estimated_1rm(weight_kg DECIMAL, reps INTEGER)
RETURNS DECIMAL
LANGUAGE plpgsql IMMUTABLE
AS $$
BEGIN
    -- Using Epley formula: 1RM = weight * (1 + reps/30)
    RETURN weight_kg * (1 + reps / 30.0);
END;
$$;

-- Trigger to update updated_at timestamps
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON public.user_profiles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_workout_programs_updated_at BEFORE UPDATE ON public.workout_programs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_workouts_updated_at BEFORE UPDATE ON public.workouts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_uploaded_files_updated_at BEFORE UPDATE ON public.uploaded_files FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();