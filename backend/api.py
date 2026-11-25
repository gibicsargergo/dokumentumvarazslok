import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, List, Optional

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
    Response,
    Cookie,
    Header,
    status
)
from pydantic import BaseModel, EmailStr

sys.path.insert(0, str(Path(__file__).resolve().parent))

from filestore import Actor, FileStore, StoredFile, UnsupportedFileType, can_delete
from rag import KnowledgeBase
from llm import stream_rag_response

# Authentikációs modulok importálása
from auth.store import AuthStore
from auth.service import AuthService, EmailAlreadyExistsError, InvalidCredentialsError
from auth.models import User

app = FastAPI(
    title="Knowledge Base API",
    description="Dokumentumalapú tudástár és kereső API",
    version="1.0.0" )

kb = KnowledgeBase()
auth_store = AuthStore() 
auth_service = AuthService(auth_store)

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    role: str

class LoginResponse(BaseModel):
    token: str
    user: UserResponse
      
files = FileStore()

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

class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_private: Optional[bool] = None

def _extract_token(session_token: Optional[str], authorization: Optional[str]) -> Optional[str]:
    '''
        Token kinyerése sütiből vagy Authorization fejlécból.
    '''
    if session_token:
        return session_token
    if authorization:
        return authorization[7:] if authorization.startswith("Bearer ") else authorization
    return None

def get_current_user(
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
) -> User:
    '''
        Munkamenet token kinyerése
    '''
    token = _extract_token(session_token, authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hiányzó autentikációs token."
        )

    user = auth_service.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Érvénytelen vagy lejárt munkamenet."
        )

    return user

def get_optional_current_user(
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    token = _extract_token(session_token, authorization)
    if not token:
        return None
    return auth_service.get_current_user(token)

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    '''
        Új felhasználó regisztrálása.
    '''
    try:
        user = auth_service.register(request.email, request.password)
        return UserResponse(id=user.id, email=user.email, role=user.role)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ez az e-mail cím már regisztrálva van."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, response: Response):
    '''
        Bejelentkezés regisztrált felhasználóval.
    '''
    try:
        user = auth_service.login(request.email, request.password)
        token = auth_service.create_session(user)

        # Süti beállítása a böngészős kliens védelméhez
        response.set_cookie(key="session_token", value=token, httponly=True)

        return LoginResponse(
            token=token,
            user = UserResponse(id=user.id, email=user.email, role=user.role)
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Érvénytelen e-mail cím vagy jelszó."
        )

@app.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    '''
        Az aktuálisan bejelentkezett felhasználó adatainak lekérése.
    '''
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role
    )

@app.post("/auth/logout")
def logout(
    response: Response,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    '''
        Session törlése az adatbázisból.
    '''
    token = _extract_token(session_token, authorization)
    if token:
        auth_service.logout(token)
    response.delete_cookie("session_token")
    return {"status": "success", "message": "Sikeres kijelentkezés."}

@app.post("/add")
def add_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    is_private: bool = Form(False),
    current_user: User = Depends(get_current_user)
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
            uploader_id=current_user.id,
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
def search_chunks(
    request: SearchRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    '''
        Keresés a tudástárban koszinusz hasonlóság, BM25 és Fuzzy matching reranking alapján.
        Dokumentumok láthatósága:
        - Nem bejelentkezett felhasználó: csak publikus dokumentumok.
        - Bejelentkezett felhasználó: publikus + saját dokumentumok.
        - Adminisztrátor: az összes dokumentum.
    '''
    viewer_id = current_user.id if current_user else None
    see_all = (current_user.role == "admin") if current_user else False
    
    try:
        results = kb.search(
            query=request.query,
            k=request.k,
            viewer_id=viewer_id,
            see_all=see_all
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keresési hiba: {str(e)}")

@app.patch("/documents/{id}")
def update_document(
    id: str,
    request: UpdateDocumentRequest,
    current_user: User = Depends(get_current_user)
):
    '''
        Dokumentum metaadatainak frissítése.
    '''
    existing = kb.collection.get(where={"doc_id": id}, include=["metadatas"])
    metadatas = existing.get("metadatas") or []

    if not metadatas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nem található dokumentum a megadott azonosítóval: {id}"
        )

    # Jogosultság ellenőrzése
    first_meta = metadatas[0] if isinstance(metadatas, list) and len(metadatas) > 0 else {}
    doc_uploader_id = first_meta.get("uploader_id")

    if current_user.role != "admin" and doc_uploader_id != current_user.id:
        raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Nincs jogosultságod más felhasználó dokumentumának módosítására."
        )

    updated_chunks = 0

    if any(v is not None for v in [request.title, request.category, request.tags]):
        updated_chunks = kb.update_metadata(
            id,
            title=request.title,
            category=request.category,
            tags=request.tags
        )

    if request.is_private is not None:
        updated_chunks = kb.set_visibility(id, is_private=request.is_private)
    
    return {"status": "success", "doc_id": id, "updated_chunks": updated_chunks}

@app.delete("/delete")
def delete_document(
    request: DeleteRequest,
    current_user: User = Depends(get_current_user)
):
    '''
        Dokumentum és annak összes chunkjának törlése a vektoradatbázisból és a tárolóból.
    '''
    existing = kb.collection.get(where={"doc_id": request.file_id}, include=["metadatas"])
    metadatas = existing.get("metadatas") or []

    if not metadatas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nem található dokumentum a megadott azonosítóval: {request.file_id}"
        )

    # Jogosultság ellenőrzése
    doc_uploader_id = metadatas[0].get("uploader_id")
    if current_user.role != "admin" and doc_uploader_id != current_user.id:
        raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Nincs jogosultságod más felhasználó dokumentumának törlésére."
        )

    # Törlés
    deleted_chunks = kb.delete(request.file_id)
    return {
        "status": "success",
        "doc_id": request.file_id,
        "deleted_chunks": deleted_chunks
    }

@app.get("/documents")
def list_documents(current_user: Optional[User] = Depends(get_optional_current_user)):
    '''
        Eltárolt dokumentumok kilistázása.
    '''
    all_docs = kb.list_documents()

    # Az admin felhasználó szűrés nélkül minden dokumentumot megkap
    if current_user and current_user.role == "admin":
        return all_docs

    # Az átlagos felhasználó csak a saját és a publikus dokumentumokat láthatja
    filtered_docs = []
    for doc in all_docs:
        is_private = doc.get("is_private", False)
        uploader_id = doc.get("uploader_id", "")

        if not is_private:
            filtered_docs.append(doc)
        elif current_user and uploader_id == current_user.id:
            filtered_docs.append(doc)

    return filtered_docs

@app.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    '''
        WebSocket endpoint az LLM streaming kommunikációhoz.
    '''
    await websocket.accept()

    token = websocket.query_params.get("token") or websocket.cookies.get("session_token")
    user = auth_service.get_current_user(token) if token else None

    viewer_id = user.id if user else None
    see_all = (user.role == "admin") if user else False

    try:
        while True:
            user_query = await websocket.receive_text()

            if user_query.strip() == "__CLOSE__":
                await websocket.close()
                break

            # Üres bemenetek figyelmen kívül hagyása
            if not user_query.strip():
                continue

            try:
                # Keresés a felhasználó jogosultsági szintjével
                hits = kb.search(
                    query=user_query,
                    viewer_id=viewer_id,
                    see_all=see_all
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