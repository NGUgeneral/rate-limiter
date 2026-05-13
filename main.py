from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Project": "Distributed Rate Limiter", "Status": "Initialized"}

@app.get("/check")
def check_limit():
    # This is where the Redis logic will eventually go
    return {"allowed": True, "remaining": 10}