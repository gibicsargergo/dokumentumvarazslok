import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from filestore import Actor, FileStore, StoredFile, UnsupportedFileType, can_delete
from rag import KnowledgeBase
from llm import stream_rag_response

app = FastAPI(
    title="Knowledge Base API",
    description="Dokumentumalapú tudástár és kereső API",
    version="1.0.0" )

kb = KnowledgeBase()
files = FileStore()

# IDEIGLENES: minden kérés ezzel a beégetett admin felhasználóval fut.
ACTOR = Actor(user_id="admin", role="admin")

def file_response(stored: StoredFile) -> dict[str, Any]:
    '''A tárolt fájl metaadatai a kliens számára (a szerveroldali útvonal nélkül).'''
    data = stored.to_dict()
    data.pop("path", None)
    return data

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
    file_id: str

@app.post("/add")
def add_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None), # Címkék vesszővel elválasztva(!)
    is_private: bool = Form(False),
):
    '''
        Új fájl feltöltése: az eredeti fájl és metaadatai a FileStore-ba kerülnek,
        majd a kb.add() kinyeri a szöveget (OCR-rel), chunkol és beágyaz.
        Ha az indexelés nem sikerül, a fájl ettől még tárolva marad.
    '''
    if not file.filename:
        raise HTTPException(status_code=400, detail="A feltöltött fájlnak nincs neve.")
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    # 1) Eredeti fájl + metaadatok mentése
    try:
        stored = files.save(
            file.file,
            filename=file.filename,
            uploader_id=ACTOR.user_id,
            name=title,
            category=category or "",
            labels=tags_list,
            is_private=is_private,
        )
    except UnsupportedFileType as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2) Szövegkinyerés + indexelés
    try:
        result = kb.add(
            stored.path,
            title=stored.name,
            category=stored.category,
            tags=list(stored.labels),
            uploader_id=stored.uploader_id,
            is_private=stored.is_private,
        )
    except Exception as e:
        return {
            "status": "stored",
            "indexed": False,
            "error": f"Hiba a fájl feldolgozásakor: {str(e)}",
            "chunks_created": 0,
            "file": file_response(stored),
        }

    if result["chunks"]:
        files.set_index_id(stored.id, result["id"])
        stored = files.get(stored.id) or stored
    return {
        "status": "success",
        "indexed": bool(result["chunks"]),
        "chunks_created": result["chunks"],
        "file": file_response(stored),
    }

@app.post("/search", response_model=List[SearchHitResponse])
def search_chunks(request: SearchRequest):
    '''
        Keresés a tudástárban koszinusz hasonlóság, BM25 és Fuzzy matching reranking alapján.
    '''
    try:
        results = kb.search(
            query=request.query,
            k=request.k,
            viewer_id=ACTOR.user_id,
            see_all=ACTOR.is_admin,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keresési hiba: {str(e)}")

@app.delete("/delete")
def delete_document(request: DeleteRequest):
    '''
        Dokumentum törlése a tárolóból, és összes chunkjának törlése a vektoradatbázisból.
    '''
    stored = files.get(request.file_id, viewer=ACTOR)
    if stored is None:
        raise HTTPException(status_code=404, detail=f"Nem található dokumentum a megadott azonosítóval: {request.file_id}")
    if not can_delete(ACTOR, stored):
        raise HTTPException(status_code=403, detail="Dokumentumot csak adminisztrátor törölhet.")

    deleted_chunks = kb.delete(stored.index_id) if stored.index_id else 0
    files.delete(stored.id, actor=ACTOR)
    return {
        "status": "success",
        "file_id": stored.id,
        "deleted_chunks": deleted_chunks }

@app.get("/documents")
def list_documents():
    '''
        A felhasználó számára látható dokumentumok metaadatai, legújabb elöl.
    '''
    return [file_response(f) for f in files.list_files(viewer=ACTOR)]

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
                hits = kb.search(
                    query=user_query,
                    viewer_id=ACTOR.user_id,
                    see_all=ACTOR.is_admin,
                )

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