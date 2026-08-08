# CORE MODULE: Vector RAM Initialization
# DOMAIN: Self-Sovereign Memory Mapping (MAC_LOCAL)

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import time

class GenesisMatrix:
    def __init__(self, dimension: int = 384):
        # Initialize the embedding model (runs 100% locally)
        print("[SYSTEM] Loading localized embedding model...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = dimension
        
        # Initialize the FAISS Vector Index (The blank spatial mapping)
        self.index = faiss.IndexFlatL2(self.dimension)
        self.ledger = []
        print(f"[SYSTEM] Vector Space Initialized. Dimensions: {self.dimension}. Status: EMPTY")

    def transmute_and_store(self, raw_text: str, classification: str):
        """
        Converts human language into a mathematical tensor and permanently 
        maps it into the local vector space.
        """
        # 1. Transmute (Embed)
        vector = self.encoder.encode([raw_text])
        
        # 2. Saturate (Add to FAISS)
        self.index.add(np.array(vector, dtype=np.float32))
        
        # 3. Crystallize (Record Metadata)
        timestamp = time.time()
        self.ledger.append({
            "id": len(self.ledger),
            "classification": classification,
            "text": raw_text,
            "timestamp": timestamp
        })
        print(f"[CRYSTALLIZED] ID: {len(self.ledger)-1} | Class: {classification} | Vectors Saturated.")

# --- Execution ---
if __name__ == "__main__":
    matrix = GenesisMatrix()
    # The system is now online, waiting for the first data infusion.
