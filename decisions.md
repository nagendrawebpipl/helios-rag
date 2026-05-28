# Architectural Decisions

## Retrieval strategy
TF-IDF cosine similarity over the combined question + answer + category text of each FAQ entry. With only 200 entries the vocabulary fits entirely in memory; there is no need for a vector database or an embedding API call at query time. Top-5 entries are passed to the LLM.

## Embedding choice
Pure TF-IDF using stdlib re and math. No external ML libraries needed. Eliminates network dependencies inside the sandbox and keeps the Docker image small.

## Chunk size
Each FAQ entry is one chunk (question + answer ~60-120 tokens). Entries are already atomic Q&A pairs so further splitting would break semantic coherence.

## LLM usage
claude-sonnet-4-20250514 generates 2-4 sentence answers grounded strictly in retrieved context. System prompt forbids hallucination and requires source citations. Falls back to best-match answer if API key is absent.

## Robustness
Zero-result queries return a clean not-found message. Ambiguous questions benefit from top-5 retrieval so the model can synthesise across related entries.
