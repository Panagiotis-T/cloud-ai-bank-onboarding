# Architecture Design

## 1. System Overview

### Business Problem
Cloud AI Bank receives high volumes of onboarding applications across the Nordics (DK, SE, NO, FI). The current workflow includes phone calls, manual document checks, emails, and manual data entry, which is slow, error-prone, and non-scalable.

### Solution Goals
Build a simple agentic GenAI onboarding assistant that automates the customer intake flow and will serve as proof of concept:

1. **Chat-based interaction**
2. **Retrieve onboarding and business requirements (RAG)**
3. **Verify identity via national registry lookup**
4. **Request user's confirmation for onboarding**
5. **Create customer records via mock API**

### Key Requirements
- Support country-specific onboarding rules and documents
- Use vector search for requirements
- Validate identity using national registries
- Map addresses → branches
- Integrate with mock REST APIs
- Maintain multi-turn conversation context

## 2. High-Level Architecture

### Architecture Diagram
```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                          │
│                     React + Tailwind CSS                        │
│             (Chat Interface with session management)            │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST
                             │ (CORS enabled)
┌────────────────────────────▼────────────────────────────────────┐
│                        API GATEWAY LAYER                        │
│                      FastAPI (Port 8000)                        │
│                         Routes: /chat                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                      AGENTIC LAYER                               │
│                   LangChain ReAct Agent                          │
│                   (Ollama model)                                 │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    AGENT TOOLS                              │ │
│  │  ┌────────────┐  ┌────────────┐  ┌───────────┐ ┌───────────┐│ │
│  │  │ vector_rag │  │ branch_    │  │ registry_ │ │ verify_   ││ │
│  │  │            │  │  lookup    │  │ lookup    │ │ residence_││ │
│  │  └────────────┘  └──────┬─────┘  └──────┬────┘ │ permit    ││ │
│  │                         │               │      └─────┬─────┘│ │
│  │  ┌──────────────────────▼───────────────▼────────────▼─┐    │ │
│  │  │               customer_create                       │    │ │
│  │  └─────────────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────┬──────────────────┬───────────────┬─────────────────────┘
          │                  │               │  
          │ Semantic Search  │ API Calls     │ API Calls
          │                  │               │ 
┌─────────▼─────┐  ┌─────────▼─────┐  ┌──────▼───────────┐
│  VECTOR STORE │  │ NATIONAL      │  │ CUSTOMER API     │
│  FAISS        │  │ REGISTRIES    │  │ (Mock REST)      │
│               │  │ (Mock APIs)   │  │                  │
│ • Appendix I  │  │ • DK,SE,NO,FI │  │   • SQLite DB    │
│ • Appendix II │  │               │  │                  │
│               │  │               │  │                  │
└───────────────┘  └───────────────┘  └──────────────────┘
         ▲
         │ Ingest & Embed
         │
┌────────┴─────────┐
│  DATA INGESTION  │
│                  │
│  • PDF Extract   │
│  • Chunking      │
│  • Embeddings    │
│                  │
└──────────────────┘
```

### Flow Description

1. **User → Frontend**: User interacts via chat interface
2. **Frontend → API**: HTTP POST to `/chat` with message + session_id
3. **API → Agent**: FastAPI invokes conversational agent
4. **Agent → Tools**: ReAct loop selects appropriate tools
5. **Tools → Data Sources**: Query vector store, registries, APIs
6. **Agent → API**: Returns formatted response
7. **API → Frontend**: JSON response displayed to user

## 3. Component Design

### 3.1 Agentic AI Layer

**Framework**: LangChain with ReAct (Reasoning + Acting) pattern

**LLM**: Ollama `gpt-oss:20b` 
- Runs locally (data privacy)
- No external API calls
- Good balance of performance and resource usage

For better performance the cloud-hosted `gpt-oss:120b-cloud` can be used.

**Agent Architecture**:
```python
ReAct Agent (create_react_agent)
├── Prompt Template (defines workflow rules)
├── Tools (5 functions the agent can call)
├── Memory (InMemoryChatMessageHistory per session)
└── Executor (max 10 iterations, error handling)
```

**Agent Tools**:

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `vector_rag` | Query business rules from knowledge base | Search query | Relevant document chunks |
| `registry_lookup` | Verify customer in national registry | "COUNTRY ID" | Customer data + verification status |
| `verify_residence_permit` | Verify customer's residency permit | JSON (user_input and expected_rp) | Verification status
| `customer_create` | Create customer in banking system | JSON (identity + address) | Customer key |
| `branch_lookup` | Find responsible branch | "COUNTRY postal_code" | Branch details |

**Workflow Logic**:
1. Detect if query is informational or registration
2. For registration: collect country + ID → verify → ask confirmation → create → route
3. Apply dynamic business rules (age validation and residence permit validation, separate from vector store)
4. For info: use RAG to retrieve business rules
5. Maintain context across conversation turns

### 3.2 RAG Pipeline

**Document Sources**:
- Appendix I: Country-specific document requirements
- Appendix II: Regional branch mappings

**Pipeline Steps**:
```
PDF Files → Extract Text → Clean → Chunk → Embed → Store
   ↓            ↓            ↓       ↓       ↓       ↓
PyMuPDF    Regex/cleanup   Regex/  Semantic  FAISS   JSON
                           logic    Split   Encoder  Metadata
```

**Chunking Strategy**:
- **Semantic chunking** by country sections
- Split on country headers: `Denmark:`, `Sweden:`, etc.
- Preserves complete rule sets per country
- Each chunk = 1 country's complete requirements

**Embedding Model**: `all-MiniLM-L6-v2`
- 384 dimensional vectors
- Fast inference, suitable for semantic document retrieval

**Vector Store**: FAISS (Facebook AI Similarity Search)
- IndexFlatIP (inner product similarity)
- L2 normalized embeddings (cosine similarity)
- ~10 chunks total (lightweight)
- Metadata includes: source, chunk_id, text

**Retrieval**: 
- Top-K search (K=5)
- Similarity threshold: 0.45
- Returns ranked results with metadata

### 3.3 National Registry Integration

**Purpose**: Verify customer identity and retrieve address data

**Mock Implementation** (real APIs follow same pattern):
```python
GET https://registry.{country}/lookup/{id}
Returns: firstName, lastName, DOB, address, citizenship
```

**Supported Countries**:
- Denmark: CPR
- Sweden: Skatteverket
- Norway: D-number system
- Finland: Personal identity code

**Tool Logic**:
- Parse country code + ID
- Query mock registry
- Check if customer already exists in DB
- Return structured JSON with all data

### 3.4 Customer API

**Specification**: Based on Appendix IV (Swagger definition)

**Endpoint**: `POST /customers/personal`

**Request Schema**:
```json
{
  "identity": {
    "externalCustomerKey": {"key": "...", "type": "DanishNationalId"},
    "name": {"firstName": "...", "lastName": "..."}
  },
  "contactInformation": {
    "address": [{...full address object...}]
  }
}
```

**Implementation**:
- Pydantic models for validation
- SQLite database for storage
- Prevent duplicates by checking ```externalCustomerKey```
- Returns UUID as ```customer key```

### 3.5 Frontend Layer

**Technology**: React 18 + Vite + Tailwind CSS

**Features**:
- Real-time chat interface
- Auto-generated session IDs
- Message history display
- Loading indicators

**API Communication**: Axios HTTP client
- POST `/chat` endpoint
- Session management

**Key Components**:
- `App.jsx`: Main chat interface with state management
- Message rendering (user vs agent)
- Input form with validation

## 4. Technology Choices & Justifications

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **LLM** | Ollama (gpt-oss:20b) | Local deployment, data privacy, no API costs |
| **Agent Framework** | LangChain ReAct | Combines reasoning + actions, enabling transparent step-by-step decision-making, tool calling, memory management |
| **Vector DB** | FAISS | Fast similarity search, lightweight, easy to embed locally, and ideal for low-latency RAG without running a full database server. |
| **Embeddings** | sentence-transformers | High-quality open-source embeddings with strong performance across tasks, all runnable locally. |
| **API** | FastAPI | Modern, async Python framework offering fast development, automatic documentation, and excellent performance for backed APIs. |
| **Frontend** | React + Vite | Modern, fast builds for rapid UI development, component reusability |
| **Styling** | Tailwind CSS | Usage of predefined classes, rapid prototyping and minimal custom CSS overhead|
| **Database** | SQLite | Serverless, embedded, ideal for lightweight applications and local deployments|
| **IaC/Deployment** | Docker + Docker Compose | Docker packages the entire application and all its dependencies (Python, Node.js, Ollama) into portable containers. This allows to run the complete system locally with a single `docker-compose up` command. For a proof-of-concept project, this approach is simple and effective. |

## 5. RAG Strategy Summary

**Chunking**: Semantic splitting by country (preserves complete rule sets)

**Embeddings**: 384-dim vectors via all-MiniLM-L6-v2

**Storage**: FAISS with metadata (source, chunk_id, text)

**Retrieval**: Top-5 cosine similarity, threshold 0.45

## 6. Current Limitations & Production Improvements

### Current Limitations
- In-memory session storage (lost on restart)
- Mock national registry APIs
- No authentication/authorization
- Single LLM instance (bottleneck if multiple users interact simultaneously)
- SQLite (not for concurrent writes)

### Production Recommendations
- **Persistence**: PostgreSQL for sessions and customer data to handle concurrent writes
- **Security**: JWT auth, API keys, HTTPS for encryption
- **Monitoring**: Logging and metrics (Prometheus?Grafana), LLM tracing (LangSmith), monitor token usage
- **Cloud Platform/Scaling**: AWS ECS for multiple LLM replicas and multiple container deployment (Docker) with auto-scaling, vector DB clustering with managed vector DB (Pinecone)
- **Cost**: Implement caching for repeated FAISS searches, registry lookups
- **Compliance**: Audit logs (tracing all actions performed), GDPR compliance (data minimization, user data deletion), data encryption (HTTPS, encrypted databases)
- **Infrastructure as Code**: Terraform for cloud resource provisioning (VMs, networks, load balancers, managed databases). Modular architecture with separate environments (dev/staging/prod). Infrastructure versioning alongside application code.
- **Dynamic Business Rules (Document Support)**: Implement file upload functionality allowing users to provide additional documents (PDFs, financial statements, etc.) during conversations. Temporary indexing and RAG integration for session-specific context.