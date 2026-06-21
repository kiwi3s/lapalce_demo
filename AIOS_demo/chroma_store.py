import os
os.environ["ANONYMIZED_TELEMETRY"] = "false"
import chromadb
from chromadb.config import Settings
from config import settings

client = chromadb.PersistentClient(path=settings.chroma_path)
collection = client.get_or_create_collection("knowledge_assets")

