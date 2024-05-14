# import uvicorn
from fastapi import FastAPI
import routes.csv.csv_router as csv_router
import routes.docs.docs_router as docs_router
import routes.images.images_router as images_router

app = FastAPI()

app.include_router(csv_router.router)
app.include_router(docs_router.router)
app.include_router(images_router.router)

@app.get('/')
async def root():
    return {"message": "Hello World"}

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)