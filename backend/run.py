import uvicorn
from app.main import app
import multiprocessing
import os

if __name__ == "__main__":
    multiprocessing.freeze_support()
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
