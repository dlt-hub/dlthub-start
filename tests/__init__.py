import os

# Prevent the suite from emitting real telemetry. Individual tests may opt back in
os.environ.setdefault("DLTHUB_START_TELEMETRY", "0")
