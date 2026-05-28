# Helios FAQ RAG Pipeline

RAG pipeline that answers Helios customer questions using 200 FAQ entries.

## How it works
1. Builds a TF-IDF index over all FAQ entries at startup
2. Scores each FAQ entry against the query using cosine similarity, returns top-5
3. Sends retrieved context to claude-sonnet-4-20250514 with source citations
4. Writes results.json in the required format

## Environment variables
- ANTHROPIC_API_KEY: Claude API key (fallback mode if unset)
- TEST_INPUTS_PATH: default /workspace/test_inputs.json
- RESULTS_PATH: default /workspace/results.json

## Dependencies
None - pure Python 3.12 stdlib only.
