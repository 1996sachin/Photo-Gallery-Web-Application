import os
from dotenv import load_dotenv
import uvicorn

if __name__ == "__main__":
    load_dotenv()
    # Get port from environment variable APP_URL or default to 8000
    app_url = os.getenv("APP_URL", "http://localhost:8000")
    try:
        port = int(app_url.split(":")[-1].split("/")[0])
    except:
        port = 8000
        
    print(f"Starting server on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
