import os
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
# 🔹 Config
EMBEDDING_MODEL = "dangvantuan/sentence-camembert-base"
FAISS_INDEX_PATH = os.path.join(os.path.dirname(__file__), "../models")  # chemin relatif vers le dossier models
TOP_K = 100 # nombre de résultats à retourner pour tester 

# Charger le vectorstore FAISS

hf_embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
vectorstore = FAISS.load_local(
    FAISS_INDEX_PATH,
    hf_embeddings,
    allow_dangerous_deserialization=True
)

print(f"✅ Index FAISS chargé avec {len(vectorstore.docstore._dict)} documents")

def search_vector_db(query: str, top_k: int = TOP_K):
    """Recherche de similarité dans FAISS + scores cosinus"""
    # Embedding de la requête
    q_emb = hf_embeddings.embed_query(query)
    
    # Recherche FAISS
    docs_with_scores = vectorstore.similarity_search_with_score(query, k=top_k)

    # Embeddings des chunks pour recalcul cosinus
    top_chunk_texts = [doc.page_content for doc, _ in docs_with_scores]
    top_chunk_embs = np.array([hf_embeddings.embed_query(text) for text in top_chunk_texts])

    # Cosine similarity
    q_emb_norm = q_emb / np.linalg.norm(q_emb)
    top_chunk_embs_norm = top_chunk_embs / np.linalg.norm(top_chunk_embs, axis=1, keepdims=True)
    cos_sims = np.dot(top_chunk_embs_norm, q_emb_norm.T).flatten()

    results = []
    for rank, ((doc, score), sim) in enumerate(zip(docs_with_scores, cos_sims), 1):
        results.append({

            "rank": rank,
            "chunk": doc.page_content[:500],  # tronqué
            "source": doc.metadata.get("source", "N/A"),
            "faiss_score": float(score),
            "cosine_similarity": float(sim),
        })

    return results
