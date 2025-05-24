from fastapi import FastAPI

app = FastAPI(title="Price Comparison Bot")

@app.get("/")
def read_root():
    return {"message": "Hello! Your bot is working!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
