FROM python:3.12-slim
WORKDIR /app
COPY helios-rag-single.py .
ENV TEST_INPUTS_PATH=/workspace/test_inputs.json
ENV RESULTS_PATH=/workspace/results.json
CMD ["python", "helios-rag-single.py"]