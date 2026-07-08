import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello"}

if __name__ == "__main__":
    import uvicorn
    import threading
    import time
    
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=8001)
        
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(2)
    
    resp = httpx.options("http://127.0.0.1:8001/", headers={
        "Origin": "https://frontend.com",
        "Access-Control-Request-Method": "GET"
    })
    print(resp.headers)
