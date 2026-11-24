import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from rag import KnowledgeBase
from llm import stream_rag_response

app = FastAPI(
    title="Knowledge Base API",
    description="Dokumentumalapú tudástár és kereső API",
    version="1.0.0" )

kb = KnowledgeBase()

class SearchRequest(BaseModel):
    query: str
    k: Optional[int] = 5

class SearchHitResponse(BaseModel):
    text: str
    score: float
    bm25: float
    fuzzy: float
    cosine: float
    title: str
    category: str
    tags: List[str]
    page: Optional[int] = None
    page_end: Optional[int] = None
    source: str
    filename: str
    doc_id: str

class DeleteRequest(BaseModel):
    doc_id: str

@app.post("/add")
async def add_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None), # Címkék vesszővel elválasztva(!)
):
    '''
        Új fájl feltöltése és feldolgozása.
        A mentést, szövegkinyerést (OCR-rel), chunkolást és beágyazást a kb.add() végzi.
    '''
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    # Ideiglenes mentés
    if not file.filename:
        raise HTTPException(status_code=400, detail="A feltöltött fájlnak nincs neve.")
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = kb.add(
            path=tmp_path,
            title=title or file.filename,
            category=category,
            tags=tags_list,
        )
        return{
            "status": "success",
            "doc_id": result["id"],
            "chunks_created": result["chunks"],
            "filename": file.filename,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Hiba a fájl feldolgozásakor: {str(e)}")
    finally:
        # Ideiglenes fájl eltakarítása
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/search", response_model=List[SearchHitResponse])
def search_chunks(request: SearchRequest):
    '''
        Keresés a tudástárban koszinusz hasonlóság, BM25 és Fuzzy matching reranking alapján.
    '''
    try:
        results = kb.search(query=request.query, k=request.k)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keresési hiba: {str(e)}")

@app.delete("/delete")
def delete_document(request: DeleteRequest):
    '''
        Dokumentum és annak összes chunkjának törlése a vektoradatbázisból és a tárolóból.
    '''
    deleted_chunks = kb.delete(request.doc_id)
    if deleted_chunks == 0:
        raise HTTPException(status_code=404, detail=f"Nem található dokumentum a megadott azonosítóval: {request.doc_id}")
    return {
        "status": "success",
        "doc_id": request.doc_id,
        "deleted_chunks": deleted_chunks }

@app.get("/documents") # TODO: csak azt listázza, amit a felhasználó láthat
def list_documents():
    '''
        A tudástárban eltárolt összes dokumentum metaadatainak kilistázása.
    '''
    return kb.list_documents()

@app.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    '''
    WebSocket endpoint az LLM streaming kommunikációhoz.
    '''
    await websocket.accept()
    try:
        while True: # Kilépési feltétel?
            user_query = await websocket.receive_text()

            # Explicit kilépési lehetőség
            if user_query.strip() == "__CLOSE__":
                await websocket.close()
                break


            # Üres bemenetek figyelmen kívül hagyása
            if not user_query.strip():
                continue

            try:
                # Releváns kontextus lekérése
                hits = kb.search(query=user_query)

                # Felhasznált források elküldése a kliensnek
                sources_payload = {
                    "type": "sources",
                    "sources": [
                        {
                            "title": h["title"],
                            "page": h["page"],
                            "doc_id": h["doc_id"],
                            "score": h["score"]
                        } for h in hits ]
                }
                await websocket.send_text(json.dumps(sources_payload))

                # Válasz streamelése tokenenként
                async for token in stream_rag_response(user_query, hits):
                    stream_payload = { "type": "token", "content": token }
                    await websocket.send_text(json.dumps(stream_payload))
                await websocket.send_text(json.dumps({"type": "end"}))

            except Exception as err:
                # Ha belső hiba történik nem szakítjuk meg a Websocketet
                await websocket.send_text(json.dumps({"type": "error", "message": str(err)}))
    except WebSocketDisconnect:
        print("WebSocket kapcsolat bontva.")

# TODO:
# @app.patch("/documents/{id}")
# @app.post("/register")
# @app.post("/login")
# @app.get("/me")
# @app.post("logout")