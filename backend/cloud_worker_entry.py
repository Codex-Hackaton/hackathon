import sys

sys.path.insert(0, "/var/task/src")

from penalty_app.cloud_worker import analyze_proof


handler = analyze_proof
