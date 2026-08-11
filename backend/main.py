from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/signals")
def get_signals():
    return [
        {
            "id": 1,
            "title": "AI demand remains strong",
            "summary": "Semiconductor and server demand continue to support the AI supply chain."
        },
        {
            "id": 2,
            "title": "Markets watch interest rates",
            "summary": "Investors are monitoring central bank policy and inflation data."
        }
    ]