# Nietzsche RAG Bot

A focused Retrieval-Augmented Generation app built around a narrow Nietzsche corpus and a strict set of themes: comfort, complacency, laziness, excuse-making, herd mentality, conformity, ressentiment, fear of struggle, self-overcoming, and becoming who you are.

**Live app:** https://nietzsche-rag-bot.onrender.com/

---

## Overview

Nietzsche RAG Bot is not a general-purpose philosophy chatbot. It is a constrained RAG application designed to answer within a specific psychological and existential slice of Nietzsche.

The app:

- retrieves from a curated Nietzsche corpus
- narrows replies to a declared thematic scope
- serves a custom frontend from the same FastAPI app
- returns grounded responses backed by citations
- supports local Docker-based development and Render deployment

The project is built so the backend, retrieval pipeline, data artifacts, and frontend all live in one deployable codebase.

---

## What the app does

The bot is designed for questions like:

- Why do I keep choosing comfort over difficulty?
- Is this laziness, avoidance, or real exhaustion?
- Why do I want to fit in even when I know it is flattening me?
- How would Nietzsche read excuse-making and self-deception?
- What does becoming who you are demand?

It is intentionally narrow. Broad abstract philosophy questions outside the project scope are refused instead of being answered badly.

---

## Live demo

**Production URL:**  
https://nietzsche-rag-bot.onrender.com/

---

## Screenshots

Home / chat interface
<img width="2360" height="1286" alt="IMG_2609" src="https://github.com/user-attachments/assets/ad13c220-f906-448a-b0d7-32a4262b784f" />


Example grounded answer with citations
<img width="2360" height="1320" alt="IMG_2613" src="https://github.com/user-attachments/assets/ff6f8288-e12a-488d-ab2e-3a6bcfd502fc" />
<img width="2360" height="1201" alt="IMG_2612" src="https://github.com/user-attachments/assets/1edc4b9b-3891-4521-a58e-450ab164d63e" />
<img width="2360" height="1320" alt="IMG_2613" src="https://github.com/user-attachments/assets/87a29646-789f-481b-b4bf-fb9bacfeeff9" />
<img width="2360" height="1201" alt="IMG_2612" src="https://github.com/user-attachments/assets/466490f6-e5f6-46f9-98d0-d6f96194df17" />
<img width="2356" height="1282" alt="IMG_2611" src="https://github.com/user-attachments/assets/b96ba52f-4559-424d-ac1a-d0dbc35c3c0d" />
<img width="2360" height="1110" alt="IMG_2614" src="https://github.com/user-attachments/assets/3e9360d9-672e-4d7b-8612-355dbb33cfe7" />


## Technologies Used

### Backend
- Python
- FastAPI
- Starlette responses / static file serving
- Uvicorn
- Pydantic
- python-dotenv
- Retrieval / data pipeline
- Curated Nietzsche corpus
- Extracted documents
- Cleaned documents
- Text chunks
- Interpretation cards
- TF-IDF retrieval artifacts

### Frontend
- Vanilla HTML
- Vanilla CSS
- Vanilla JavaScript

### Deployment / DevOps
- Docker
- Render
- docker-compose
- API routes

## Important Routes

- `GET /` → serves the frontend
- `GET /health` → health check
- `GET /ready` → readiness check
- `POST /chat` → grounded response generation
- `POST /retrieve` → retrieval endpoint
- `POST /debug/inspect` → debug inspection endpoint
- `GET /sources`
- `GET /extracted`
- `GET /extracted/{source_id}`
- `GET /cleaned`
- `GET /cleaned/{source_id}`
- `GET /chunks`
- `GET /chunks/{source_id}`
- `GET /cards`
- `GET /cards/{card_id}`
- 
## How it works

1. Source ingestion

Raw source material is organized under data/raw/ with separate locations for PDFs, text, and manifests.

2. Extraction

Raw source files are normalized into structured extracted documents.

3. Cleaning

The extracted text is cleaned into a more retrieval-friendly format.

4. Chunking

Long texts are split into chunks for retrieval.

5. Card building

Interpretation cards are created for recurring psychological patterns and themes.

6. Retrieval artifact build

The project builds a retrieval corpus and TF-IDF artifacts into data/vector_store/.

7. Query flow

When a user sends a message:

the frontend submits to POST /chat
the backend checks whether the message is inside scope
relevant retrieval chunks are searched
relevant cards may be matched
the backend returns a grounded response with citations
the frontend renders the answer and sources

## Project structure

```text
nietzsche-rag-bot/
├── app/
│   ├── api/
│   │   └── routes.py
│   ├── core/
│   │   └── config.py
│   ├── models/
│   │   ├── card.py
│   │   ├── chat.py
│   │   ├── cleaned.py
│   │   ├── debug.py
│   │   ├── extracted.py
│   │   ├── retrieval.py
│   │   ├── source.py
│   │   ├── vector_document.py
│   │   └── ...
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── retrieval_service.py
│   │   ├── debug_service.py
│   │   ├── source_service.py
│   │   ├── readiness_service.py
│   │   └── ...
│   └── main.py
├── data/
│   ├── raw/
│   │   ├── manifests/
│   │   ├── pdfs/
│   │   └── text/
│   ├── extracted/
│   ├── cleaned/
│   ├── chunks/
│   ├── cards/
│   └── vector_store/
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── assets/
├── scripts/
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── render.yaml
├── run.py
└── README.md
