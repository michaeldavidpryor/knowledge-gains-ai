# Knowledge Gains - Science-based Weightlifting App

A science-based weightlifting app that uses AI services powered by OpenAI's Responses API to generate personalized workout programs based on user equipment, uploaded fitness documents, and web research.

## Features

### 🤖 AI-Powered Program Generation
- **AI Services**: Specialized services for file processing, web research, and program coordination using OpenAI's Responses API
- **Multi-Source Intelligence**: Combines user-uploaded files, web research, and equipment assessment
- **Science-Based Programming**: Uses evidence-based training principles and progression schemes

### 📄 File Processing
- **PDF Analysis**: Extract workout programs from research papers and fitness documents
- **Document Intelligence**: AI analysis of uploaded fitness content (Jeff Nippard books, research papers, etc.)
- **Program Extraction**: Automatically identify and extract workout routines from documents

### 🌐 Web Research
- **Fitness-Specific Search**: Targeted searches on reputable fitness websites
- **Program Research**: Find and analyze specific workout programs online
- **Evidence Evaluation**: Assess credibility and scientific backing of sources

### 🏋️ Interactive Workout Tracking
- **Card-Based Interface**: Clean, intuitive workout cards for each exercise
- **Progressive Weight Loading**: Automatic weight suggestions based on previous workouts
- **Real-Time Tracking**: Live progress tracking with completion percentages
- **Set Management**: Weight input, editable reps, completion checkboxes, and RPE tracking
- **Exercise Modification**: AI-powered exercise substitutions during workouts

### 📊 Progress Tracking
- **Personal Records**: Automatic PR detection and tracking
- **Volume Progression**: Track training volume over time
- **1RM Estimation**: Calculate estimated one-rep maxes
- **Program Analytics**: Detailed insights into training progress

## System Architecture

### Services
- **FileProcessorService**: Processes uploaded fitness documents using file_search and code_interpreter tools
- **WebSearchService**: Searches and analyzes web content using built-in web_search tool
- **WorkoutCoordinatorService**: Orchestrates program generation with stateful conversations

### Database Schema (Supabase)
- User profiles and equipment tracking
- Workout programs with AI generation metadata
- Individual workout instances and set tracking
- Exercise database with form cues and progressions
- File upload processing and analysis
- Progression tracking and personal records

### Frontend
- **HTMX + DaisyUI**: Modern, reactive interface without complex JavaScript
- **Real-time Updates**: Live workout progress and set completion
- **Mobile-First**: Responsive design optimized for gym use
- **Progressive Enhancement**: Works without JavaScript

## Setup Instructions

### 1. Environment Setup

Create a `.env` file in the project root:

```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# App Configuration
APP_ENV=development
SECRET_KEY=your_secret_key_here
```

### 2. Database Setup

1. Create a new Supabase project
2. Run the SQL schema from `database/schema.sql` in your Supabase SQL editor
3. Enable Row Level Security (RLS) policies
4. Configure authentication settings

### 3. Installation with uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd knowledge-gains

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Setup development environment
uv run scripts/dev.py setup
```

### 4. Running the Application

```bash
# Development server with hot reload
uv run scripts/dev.py serve

# Or run directly with uv
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Alternative: activate virtual environment first
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python main.py
```

### Development Commands

```bash
# Run tests
uv run scripts/dev.py test

# Format code
uv run scripts/dev.py format

# Run linting
uv run scripts/dev.py lint

# Run all checks
uv run scripts/dev.py check

# Install pre-commit hooks
uv run scripts/dev.py install-hooks
```

Visit `http://localhost:8000` to access the application.

## Usage Guide

### 1. Program Generation

1. **Initial Request**: Describe your desired workout program
2. **Equipment Assessment**: Specify available equipment (full gym, home gym, minimal, etc.)
3. **Program Duration**: Set weeks and training frequency
4. **File Upload** (Optional): Upload fitness documents for AI analysis
5. **AI Generation**: The system creates a personalized program

### 2. Workout Execution

1. **Start Workout**: Begin tracking with automatic weight suggestions
2. **Set Tracking**: Input weights, adjust reps, track RPE, mark completion
3. **Exercise Modification**: Request AI-powered exercise substitutions
4. **Progress Monitoring**: Real-time completion percentage and rest timers
5. **Workout Completion**: Automatic progress tracking and PR detection

### 3. Program Modification

- **Exercise Substitutions**: AI-powered alternatives based on equipment/preferences
- **Weight Adjustments**: Dynamic progression based on performance
- **Schedule Changes**: Flexible training frequency modifications

## API Endpoints

### Program Generation
- `POST /api/generate-program` - Generate new workout program
- `GET /api/program/{id}` - Retrieve program details
- `POST /api/modify-exercise` - Request exercise modifications

### Workout Tracking
- `GET /workout/{id}` - Start workout session
- `POST /api/update-set` - Update set data (weight, reps, completion)
- `POST /api/finish-workout` - Complete workout session

### File Management
- `POST /api/upload-files` - Upload fitness documents
- `GET /api/file-analysis/{id}` - Get file processing results

### Progress Tracking
- `GET /api/progress/{exercise}` - Get exercise progression
- `GET /api/records` - Personal records summary

## Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Package Management**: uv (fast Python package installer)
- **Database**: Supabase (PostgreSQL)
- **AI**: OpenAI Responses API with GPT-4.1
- **Frontend**: HTMX, DaisyUI, Tailwind CSS
- **Authentication**: Supabase Auth
- **File Processing**: PyPDF2, python-docx
- **Web Scraping**: aiohttp, BeautifulSoup4
- **Development**: Black, isort, flake8, mypy, pre-commit

## Development

### Project Structure
```
knowledge-gains/
├── services/               # AI service implementations
│   ├── base_service.py
│   ├── workout_coordinator.py
│   ├── file_processor.py
│   └── web_search.py
├── templates/             # Jinja2 HTML templates
│   ├── workout_session.html
│   ├── home.html
│   └── components/
├── static/               # Static assets
├── uploads/              # User uploaded files
├── scripts/              # Development tools
├── main.py              # FastAPI application
├── pyproject.toml       # uv dependencies
└── README.md
```

### Adding New Features

1. **New Services**: Extend `BaseService` class for specialized functionality
2. **Database Changes**: Update `schema.sql` and run migrations
3. **Frontend Components**: Create reusable HTMX components
4. **API Endpoints**: Add routes in `main.py` with proper validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the setup instructions

---

Built with ❤️ for the fitness community