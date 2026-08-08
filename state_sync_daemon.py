import os
import time
import jax
import jax.numpy as jnp
import numpy as np
import warnings
from hermes_twin_executor import HermesAgenticExecutor
from genesis_memory import GenesisMatrix

warnings.filterwarnings('ignore')

def normalize_embedding_vector(vector: np.ndarray) -> np.ndarray:
    """
    Applies L2 normalization to bound the embedding space.
    Prevents magnitude drift during vector similarity search.
    """
    norm = np.linalg.norm(vector)
    return vector / (norm + 1e-9) if norm >= 1.0 else vector

# 1. VECTOR DATABASE INITIALIZATION
matrix = GenesisMatrix(dimension=384)
intent_string = "MAINTAIN_SYSTEM_STATE_SYNCHRONIZATION"

# Anchor Genesis Intent
base_vector = matrix.encoder.encode([intent_string])[0]
normalized_vector = normalize_embedding_vector(base_vector)
matrix.index.add(np.array([normalized_vector], dtype=np.float32))

# 2. EXECUTION ENGINE INSTANTIATION
executor = HermesAgenticExecutor(state_dimension=256, compression_ratio=0.15)
key = jax.random.PRNGKey(42)

# 3. CONTINUOUS TELEMETRY LOOP
cycle_count = 0
print("[Λ-LAYER] Decoupled aggregation active. Initiating continuous telemetry cascade...")

while True:
    cycle_count += 1
    
    # Ingest local CPU load metrics (1-minute average) via OS kernel
    cpu_load_1m = os.getloadavg()[0] 
    
    # Modulate deterministic base tensor with physical hardware load variance
    base_tensor = jax.random.normal(jax.random.fold_in(key, cycle_count), (256, 256)) 
    telemetry_state = base_tensor * (1.0 + cpu_load_1m)
    
    # Execute SVD tensor compression (Strict tensor input, no kwargs)
    execution_result = executor.execute_cycle(
        raw_telemetry=telemetry_state
    )
    
    # Matrix Saturation (Post-Execution Validation)
    if execution_result.compression_metrics.fidelity >= 0.85:
        record = f"STATE_HASH: {execution_result.state_fidelity_chain} | CYCLE: {cycle_count}"
        new_vec = normalize_embedding_vector(matrix.encoder.encode([record])[0])
        matrix.index.add(np.array([new_vec], dtype=np.float32))
    
    # Commit metrics to log every 5 cycles to optimize disk I/O overhead
    if cycle_count % 5 == 0:
        with open("system_telemetry.log", "a") as log_file:
            log_file.write(f"CYCLE: {cycle_count} | CPU_LOAD: {cpu_load_1m:.2f} | FIDELITY: {execution_result.compression_metrics.fidelity:.6f} | CHAIN_HASH: {execution_result.state_fidelity_chain}\n")
            log_file.flush()
        print(f"[CRYSTALLIZED] CYCLE: {cycle_count} | MATRIX_VOLUME: {matrix.index.ntotal} | CHAIN_HASH: {execution_result.state_fidelity_chain}")
            
    # Polling interval (seconds)
    time.sleep(2.718)
