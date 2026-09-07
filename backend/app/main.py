from fastapi import FastAPI
from api.v1 import bidders

app = FastAPI()

app.include_router(bidders.router)