import os

folders = [
    "app/rag",
    "app/llm",
    "app/email",
    "app/utils",
    "data/raw",
    "data/processed",
    "vector_store",
    "scripts"
]

files = [
    "app/rag/preprocess.py",
    "app/rag/chunking.py",
    "app/rag/embeddings.py",
    "app/rag/vector_store.py",
    "app/rag/retriever.py",
    "app/rag/rag_pipeline.py",

    "app/llm/llm_client.py",
    "app/llm/prompt_builder.py",

    "app/email/email_listener.py",
    "app/email/email_responder.py",

    "app/utils/config.py",

    "scripts/build_rag.py",
    "scripts/test_query.py",

    "requirements.txt",
    ".env",
    "README.md"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)

for file in files:
    open(file, "a").close()

print("Project structure created successfully")