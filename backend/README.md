# Cloud AI Bank Onboarding - Backend

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-blue.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/langchain-1.0+-blue.svg)](https://langchain.com/)

## Overview

Backend service for Cloud AI Bank's automated customer onboarding system. Built with FastAPI and LangChain, it provides an agentic AI workflow using ReAct pattern with RAG (Retrieval-Augmented Generation) for business rules retrieval.

## Prerequisites

- **Python**: 3.11 or higher
- **uv**: Python environment manager ([installation guide](https://astral.sh/uv))
- **Ollama**: Local AI runtime ([download](https://ollama.com/))

## Installation

### 1. Install uv (if not already installed)

**Unix/Linux**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows**:
```powershell
iwr -useb https://astral.sh/uv/install.ps1 | iex
```

### 2. Install Ollama and Model

Download Ollama from [ollama.com](https://ollama.com/) and install.

Pull required model:
```bash
ollama pull gpt-oss:20b
ollama list  # Verify installation
```

Or for the ``gpt-oss:120b-cloud`` model create an account and run
``ollama signin`` in the CLI to create a Public Key automatically.

### 3. Set Up Backend Environment

```bash
cd backend
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync
```

### 4. Build Vector Store

Process business documents (Appendices 1 & 2) into FAISS index:
```bash
python -m app.data_ingestion
```

Expected output: `FAISS index saved.`

### 5. Start API Server

```bash
uvicorn src.main:app --reload --port 8000
```

Access points:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health


## Usage

### Test API

Health check:
```bash
curl http://localhost:8000/health
```

Chat example:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test1", "message": "I want to open an account"}'
```

### Full Onboarding Flow

```bash
# Step 1
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "Hi, I want to become a customer"}'

# Step 2
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "DK 1304802151"}'
```

Agent will:
1. Verify identity via registry
2. Validate age requirements and residency status
3. Create customer record
4. Assign responsible branch
5. Return confirmation

## Mock Test Data

In `registry_api.py`

## Troubleshooting

**Ollama not running:**
```bash
ollama serve  # Start Ollama
```

**FAISS index missing:**
```bash
python -m app.data_ingestion
```

**Port already in use:**
```bash
uvicorn src.main:app --reload --port 9000
```

## Documentation

See [ARCHITECTURE.md](../ARCHITECTURE.md) for system design details.