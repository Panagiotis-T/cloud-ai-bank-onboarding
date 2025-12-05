# Cloud AI Bank Onboarding

AI-powered customer onboarding system for Cloud AI Bank across Nordic countries (Denmark, Sweden, Norway, Finland).

## Overview

Automated banking customer onboarding using:
- **Agentic AI** (LangChain + Ollama) for conversational onboarding
- **RAG** (FAISS + vector embeddings) for business rules retrieval
- **FastAPI** backend with REST API
- **React** frontend with real-time chat interface

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Ollama with `gpt-oss:20b` or `gpt-oss:120b-cloud` model

### 1. Backend Setup

**[Install Ollama and Model](backend/README.md#2-Install-Ollama-and-Model)**

**[Set Up Backend Environment](backend/README.md#3-set-up-backend-environment)**

### 2. Frontend Setup
**[Setup Instructions](frontend/README.md##-Setup-Instructions)**

## Deployment

### Docker Compose

>Prerequisite: Make sure Docker is installed on your machine.

Download: ```https://www.docker.com/get-started```

Run entire stack with Docker:
```bash
docker-compose -f iac/docker-compose.yml up --build
```

Access:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000/docs

Stop:
```bash
docker-compose -f iac/docker-compose.yml down
```

## Project Structure
```
cloud-ai-bank-onboarding/
├── backend/
│   ├── src/app/
│   │   ├── agent.py           # Agentic workflow (ReAct)
│   │   ├── tools.py           # Tool definitions for the agent
│   │   ├── prompts.py         # Agent prompt template
│   │   ├── helpers.py         # Helper functions etc.
│   │   ├── customer_api.py    # Customer creation API
│   │   ├── registry_api.py    # National registry
│   │   ├── mock_data.json     # Mock registry data
│   │   ├── data_ingestion.py  # RAG pipeline
│   └── main.py                # FastAPI server
│   ├── database/              # SQLite + FAISS store
│   └── docs/appendices/       # Business rules (PDFs)
├── frontend/
│   └── src/
│       ├── App.jsx            # React chat interface
│       └── main.jsx            # React app entry point
├── iac/
│    ├── docker-compose.yml
│    ├── Dockerfile.backend
│    └── Dockerfile.frontend
├── ARCHITECTURE.md            # System design
└── README.md                  #  Explanation on how to set up and run the project
```

## Features

- RAG-powered business rules/requirements retrieval
- National registry verification
- Automated branch routing
- Customer creation via mock REST API

## Documentation

- **[Backend README](backend/README.md)** - Backend infrastructure
- **[Frontend README](frontend/README.md)** - UI setup
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Design diagram

## Tech Stack

**Backend**: Python, LangChain, FastAPI, Ollama, FAISS, SQLite
**Frontend**: React, Vite, Tailwind CSS, Axios
**AI**: gpt-oss:20b (via Ollama), sentence-transformers
