import json
import os
import time
from collections import defaultdict
from typing import Optional

import chromadb
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain_chroma import Chroma
from langchain_cohere import CohereRerank
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel

load_dotenv()

# --- Database ---

def _get_db():
    url = os.environ["DATABASE_URL"]
    if "sslmode" not in url:
        url += "?sslmode=require"
    return psycopg2.connect(url)

def _init_db():
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS query_logs (
                        id          SERIAL PRIMARY KEY,
                        question    TEXT NOT NULL,
                        play_filter TEXT,
                        answer      TEXT NOT NULL,
                        sources     JSONB,
                        duration_ms INTEGER,
                        created_at  TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
        print("Database initialised successfully.")
    except Exception as e:
        print(f"Warning: could not initialise database ({type(e).__name__}: {e}). Query logging will be disabled.")

_init_db()

def _log_query(question: str, play_filter: Optional[str], answer: str, sources: list, duration_ms: int):
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO query_logs (question, play_filter, answer, sources, duration_ms) VALUES (%s, %s, %s, %s, %s)",
                    (question, play_filter, answer, json.dumps(sources), duration_ms),
                )
    except Exception:
        pass  # never let logging break a response

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Clients ---
# https://docs.langchain.com/oss/python/integrations/vectorstores/chroma#create-a-chroma-vectorstore

chroma_client = chromadb.HttpClient(
    host="api.trychroma.com",
    ssl=True, # ssl connection
    tenant=os.environ["CHROMA_TENANT_ID"],
    database=os.environ["CHROMA_DB_NAME"],
    headers={"x-chroma-token": os.environ["CHROMA_API_KEY"]},
)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore = Chroma(
    client=chroma_client,
    collection_name="shakespeare_scenes",
    embedding_function=embeddings,
)

llm = ChatOpenAI(
    model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku"),
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

# --- Startup: load all docs for BM25 ---

def _load_docs() -> list[Document]: 
    raw = chroma_client.get_collection("shakespeare_scenes").get(
        include=["documents", "metadatas"]
    )
    return [
        Document(page_content=doc, metadata=meta)
        for doc, meta in zip(raw["documents"], raw["metadatas"])
    ]

ALL_DOCS: list[Document] = _load_docs() 

DOCS_BY_PLAY: dict[str, list[Document]] = defaultdict(list)
for _doc in ALL_DOCS:
    DOCS_BY_PLAY[_doc.metadata.get("play", "")].append(_doc)

# --- Prompt ---

PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are ShakespeareGPT, a scholarly expert on Shakespeare's plays. "
        "Answer questions using the provided context. Structure every response with these markdown sections:\n\n"
        "## Context\n"
        "Brief background on the relevant play, character, or theme.\n\n"
        "## Specific Moment\n"
        "The precise scene or moment that answers the question.\n\n"
        "## Quote Specifically\n"
        "Format the passage as a markdown blockquote following these rules exactly:\n"
        "- Every single line including the citation starts with '> '\n"
        "- NO blank lines inside the blockquote — the citation immediately follows the last verse line\n"
        "- NO quotation marks (no ' \" ' characters) anywhere in the blockquote\n"
        "- NO speaker name\n"
        "- Each verse line on its own '> ' line\n"
        "- Final line: '> (Act X, Scene Y)'\n\n"
        "## Analyse the Moment\n"
        "What the passage reveals about character, theme, or dramatic significance.\n\n"
        "Keep responses concise and scholarly but accessible. Always use > for quotes."
    )),
    ("human", "Context from the plays:\n{context}\n\nQuestion: {question}"),
])

# --- Schemas ---

class AnswerRequest(BaseModel):
    question: str
    k: int = 5
    filters: Optional[dict] = None


class Source(BaseModel):
    index: int
    play: str
    act: str
    scene_title: str
    similarity: float


class AnswerResponse(BaseModel):
    answer: str
    sources: list[Source]

# --- Retrieval ---

def _build_retriever(question: str, k: int, play_filter: Optional[str]) -> ContextualCompressionRetriever:
    # Term-based: BM25 over play-filtered or full corpus
    bm25_docs = DOCS_BY_PLAY[play_filter] if play_filter else ALL_DOCS
    bm25 = BM25Retriever.from_documents(bm25_docs, k=k)

    # Semantic: ChromaDB vector search with optional metadata filter
    search_kwargs: dict = {"k": k}
    if play_filter:
        search_kwargs["filter"] = {"play": play_filter}
    semantic = vectorstore.as_retriever(search_kwargs=search_kwargs)

    # Hybrid: Reciprocal Rank Fusion (semantic weighted slightly higher)
    ensemble = EnsembleRetriever(
        retrievers=[bm25, semantic],
        weights=[0.4, 0.6],
    )

    # Rerank with Cohere
    reranker = CohereRerank(
        cohere_api_key=os.environ["COHERE_API_KEY"],
        top_n=k,
        model="rerank-v3.5",
    )
    return ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=ensemble,
    )

# --- Routes ---

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/answer", response_model=AnswerResponse)
async def answer(request: AnswerRequest):
    play_filter = request.filters.get("play") if request.filters else None
    try:
        retriever = _build_retriever(request.question, request.k, play_filter)
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"build_retriever failed: {traceback.format_exc()}")

    t0 = time.monotonic()

    try:
        docs = retriever.invoke(request.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    context = "\n\n---\n\n".join(
        f"[{d.metadata.get('play')} - {d.metadata.get('current_scene', '')}]\n{d.page_content}"
        for d in docs
    )

    try:
        response = (PROMPT | llm).invoke({"context": context, "question": request.question})
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"llm failed: {traceback.format_exc()}")

    sources = [
        Source(
            index=i,
            play=d.metadata.get("play", ""),
            act=d.metadata.get("act", ""),
            scene_title=d.metadata.get("scene_title", ""),
            similarity=round(float(d.metadata.get("relevance_score", 0.0)), 4),
        )
        for i, d in enumerate(docs)
    ]

    duration_ms = int((time.monotonic() - t0) * 1000)
    _log_query(
        question=request.question,
        play_filter=play_filter,
        answer=response.content,
        sources=[s.model_dump() for s in sources],
        duration_ms=duration_ms,
    )

    return AnswerResponse(answer=response.content, sources=sources)
