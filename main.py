import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request, UploadFile, Depends, Response, Cookie
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from chatkit.server import StreamingResult
from chatkit.types import FileAttachment, ImageAttachment

from app.server import MyChatKitServer
from app.store import SQLiteStore
from app.types import RequestContext

load_dotenv()

app = FastAPI()

# Setup persistence
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
store = SQLiteStore()
server = MyChatKitServer(store=store, attachment_store=store)

# --- FIX: User Isolation via Cookies ---
def get_user(request: Request) -> RequestContext:
    """
    Identifies unique users using the X-ChatKit-User header.
    """
    user_id = request.headers.get("x-chatkit-user")
    if not user_id:
        # Fallback for direct browser hits or misconfigured clients
        user_id = "anonymous-default"
    return RequestContext(user_id=user_id)

@app.post("/chatkit")
async def handle_chatkit(request: Request, ctx: RequestContext = Depends(get_user)):
    # This remains the same, but ctx now has the stable header-based user_id
    try:
        body = await request.body()
        result = await server.process(body, ctx)
        
        if isinstance(result, StreamingResult):
            return StreamingResponse(result, media_type="text/event-stream")
        else:
            return Response(content=result.json, media_type="application/json")
            
    except Exception as e:
        print(f"Error processing request: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/upload")
async def upload_file(file: UploadFile, ctx: RequestContext = Depends(get_user)):
    file_id = f"file_{uuid4().hex}"
    ext = Path(file.filename).suffix
    safe_filename = f"{file_id}{ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    is_image = file.content_type.startswith("image/")
    base_url = "http://localhost:8000/files"
    file_url = f"{base_url}/{safe_filename}"
    
    if is_image:
        attachment = ImageAttachment(
            type="image", id=file_id, name=file.filename,
            mime_type=file.content_type, preview_url=file_url, url=file_url
        )
    else:
        attachment = FileAttachment(
            type="file", id=file_id, name=file.filename,
            mime_type=file.content_type, url=file_url
        )
        
    await store.save_attachment(attachment, ctx)
    return attachment.model_dump(mode="json")

app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)