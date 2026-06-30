import os

# Prevent the suite from emitting real telemetry
os.environ.setdefault("DLTHUB_START_TELEMETRY", "0")
