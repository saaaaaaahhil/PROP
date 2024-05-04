# import uvicorn
from fastapi import FastAPI
import routes.csv.csv_router as csv_router

app = FastAPI()

app.include_router(csv_router.router)

@app.get('/')
async def root():
    return {"message": "Hello World"}

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)