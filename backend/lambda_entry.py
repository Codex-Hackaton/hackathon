import sys

sys.path.insert(0, "/var/task/src")

from mangum import Mangum

from penalty_app.api import app


handler = Mangum(app, lifespan="off")
