from fastapi import FastAPI
app = FastAPI(title="MercadoIA API")
@app.get("/health")
def health():
    return {"status": "ok"}
