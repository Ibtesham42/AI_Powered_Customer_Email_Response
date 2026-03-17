from sentence_transformers import SentenceTransformer
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"

model = SentenceTransformer(
    "BAAI/bge-base-en-v1.5",
    device=device
)

print("Running on:", device)