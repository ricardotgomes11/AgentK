import os, time
while True:
    try:
        # Atomic state pulse
        with open("/tmp/heartbeat.status", "w") as f: f.write(f"TS:{time.time()}")
        time.sleep(3600)
    except: pass
