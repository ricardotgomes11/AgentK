import os
import time
import requests
import numpy as np
import warnings
import jax
from hermes_twin_executor import HermesAgenticExecutor
from genesis_memory import GenesisMatrix

warnings.filterwarnings('ignore')

# 1. INITIALIZATION
matrix = GenesisMatrix(dimension=384)
executor = HermesAgenticExecutor(state_dimension=256, compression_ratio=0.15)
key = jax.random.PRNGKey(42)

# Circuit breaker state
network_active = True
last_fail_time = 0

print("[Λ-LAYER] Daemon active with Circuit Breaker enabled.")

cycle_count = 0
while True:
    cycle_count += 1
    cpu_load_1m = os.getloadavg()[0] 
    
    # [OSINT] Circuit-Breaker Logic
    macro_variance = 1.0
    if network_active:
        try:
            # Short timeout for high-frequency polling
            response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json", timeout=2)
            macro_variance = 1.0 + (response.json()["bpi"]["USD"]["rate_float"] / 1000000.0)
        except:
            network_active = False
            last_fail_time = time.time()
            print("[ETL: NETWORK FAULT] Circuit opened. Defaulting to 1.0 variance.")
    elif time.time() - last_fail_time > 60: # Attempt retry every 60s
        network_active = True
        print("[ETL: NETWORK RECOVERY] Attempting re-connection...")

    # [FUSION]
    base_tensor = jax.random.normal(jax.random.fold_in(key, cycle_count), (256, 256)) 
    telemetry_state = base_tensor * (cpu_load_1m + macro_variance)
    
    res = executor.execute_cycle(raw_telemetry=telemetry_state)
    
    # [LOGGING]
    if cycle_count % 5 == 0:
        with open("system_telemetry.log", "a") as log:
            log.write(f"CYCLE: {cycle_count} | MACRO: {macro_variance:.6f} | FIDELITY: {res.compression_metrics.fidelity:.6f}\n")
        print(f"[CYCLE {cycle_count}] FIDELITY: {res.compression_metrics.fidelity:.6f}")

    time.sleep(2.718)
