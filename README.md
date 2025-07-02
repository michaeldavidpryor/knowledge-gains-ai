# Knowledge Gains - Science-based Weightlifting App

This repository contains **Knowledge Gains**, a comprehensive science-based weightlifting application with AI agents for personalized workout program generation.

## 🏋️ Project Location

The complete Knowledge Gains application is located in the `knowledge_gains/` directory.

```bash
cd knowledge_gains/
```

## 🚀 Quick Start

```bash
# Navigate to the project
cd knowledge_gains/

# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup and run
uv sync
uv run scripts/dev.py setup
uv run scripts/dev.py serve
```

## 📖 Full Documentation

See the complete documentation in `knowledge_gains/README.md` for:

- ✅ AI-powered program generation with specialized fitness agents
- ✅ Interactive workout tracking with card-based interface
- ✅ File processing for fitness documents (PDFs, research papers)
- ✅ Web research for program validation
- ✅ Supabase integration for data persistence
- ✅ Modern HTMX + DaisyUI frontend

## 🎯 Features

- **WeightliftingCoordinator**: AI agent for science-based program generation
- **FileProcessorAgent**: Processes fitness documents and research papers
- **FitnessWebAgent**: Searches and analyzes fitness websites
- **Interactive Tracking**: Card-based workout interface with weight progression
- **Equipment Assessment**: Automatically determines required equipment
- **Program Duration Planning**: Plans training frequency and duration

---

**Navigate to `knowledge_gains/` directory for the complete application.**