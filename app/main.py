from fastapi import FastAPI

app = FastAPI(
    title="Veggie Rescue Deliveries API",
    description="Equitable food rescue delivery recommendation system.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}