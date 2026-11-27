import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Any, List, Literal, Optional

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    Query,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
    Response,
    Cookie,
    Header,
    status
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr

sys.path.insert(0, str(Path(__file__).resolve().parent))

from filestore import Actor, FileStore, StoredFile, UnsupportedFileType, can_delete
from rag import KnowledgeBase
from llm import stream_rag_response
from stats import Mode, QueryHit, StatsStore
from stats.config import DEFAULT_MONTHS

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
stats = StatsStore()

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

def attach_file_ids(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    '''A keresési találatokhoz hozzáadja a FileStore azonosítót (file_id).'''
    cache: dict[str, Optional[str]] = {}
    for h in hits:
        doc_id = h["doc_id"]
        if doc_id not in cache:
            stored = files.get_by_index_id(doc_id)  # belső hozzáférés: a kb már szűrt
            cache[doc_id] = stored.id if stored else None
        h["file_id"] = cache[doc_id]
    return hits

def log_query(user_id: Optional[str], mode: Mode, query: str, hits: list[dict[str, Any]]) -> Optional[int]:
    '''Kérdés és találatai naplózása. Hiba esetén nem akasztja meg a keresést.'''
    try:
        return stats.log_query(
            user_id=user_id or "anonymous",
            mode=mode,
            query=query,
            hits=[
                QueryHit(
                    file_id=h.get("file_id"),
                    title=h["title"],
                    category=h["category"],
                    rank=i,
                    score=h["score"],
                )
                for i, h in enumerate(hits)
            ],
        )
    except Exception as err:
        print(f"[stats] naplózási hiba: {err}")
        return None

def record_answer(query_id: Optional[int], *, answer: Optional[str] = None, error: Optional[str] = None) -> None:
    '''A chat válaszának (vagy hibájának) hozzáfűzése a naplózott kérdéshez.'''
    if query_id is None:
        return
    try:
        stats.record_answer(query_id, answer=answer, error=error)
    except Exception as err:
        print(f"[stats] naplózási hiba: {err}")

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
    file_id: Optional[str] = None

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

class StatItem(BaseModel):
    id: str
    label: str
    monthly: List[int]

class SearchStats(BaseModel):
    months: List[str]
    items: List[StatItem]

class SearchStatsResponse(BaseModel):
    documents: SearchStats
    categories: SearchStats

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keresési hiba: {str(e)}")
    attach_file_ids(results)
    log_query(viewer_id, "search", request.query, results)
    return results

@app.patch("/documents/{id}")
def update_document(
    id: str,
    request: UpdateDocumentRequest,
    current_user: User = Depends(get_current_user)
):
    '''
        Dokumentum metaadatainak frissítése.
    '''
    actor = Actor(user_id=current_user.id, role=current_user.role)
    
    stored = files.get(id, viewer=actor) or files.get_by_index_id(id, viewer=actor)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nem található dokumentum a megadott azonosítóval: {id}"
        )
    
    if not (actor.is_admin or stored.uploader_id == actor.user_id):
        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Nincs jogosultságod más felhasználó dokumentumának módosítására."
        )

    updated_file = files.update(
        stored.id,
        actor=actor,
        name=request.title,
        category=request.category,
        labels=request.tags,
        is_private=request.is_private
    )    

    updated_chunks = 0
    index_id = stored.index_id or stored.id

    if any(v is not None for v in [request.title, request.category, request.tags]):
        updated_chunks = kb.update_metadata(
            index_id,
            title=request.title,
            category=request.category,
            tags=request.tags
        )

    if request.is_private is not None:
        updated_chunks = kb.set_visibility(index_id, is_private=request.is_private)
    
    return {
        "status": "success",
        "file_id": updated_file.id,
        "index_id": index_id,
        "updated_chunks": updated_chunks
    }

@app.delete("/delete")
def delete_document(
    request: DeleteRequest,
    current_user: User = Depends(get_current_user)
):
    '''
        Dokumentum és annak összes chunkjának törlése a vektoradatbázisból és a tárolóból.
    '''
    actor = Actor(user_id=current_user.id, role=current_user.role)

    stored = files.get(request.file_id, viewer=actor) or files.get_by_index_id(request.file_id, viewer=actor)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nem található dokumentum a megadott azonosítóval: {request.file_id}"
        )

    if not (actor.is_admin or stored.uploader_id == actor.user_id):
        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Nincs jogosultságod más felhasználó dokumentumának törlésére."
        )

    index_id = stored.index_id or stored.id
    deleted_chunks = kb.delete(index_id) if index_id else 0
    files.delete(stored.id, actor=actor)

    return {
        "status": "success",
        "file_id": stored.id,
        "index_id": index_id,
        "deleted_chunks": deleted_chunks
    }

class DocumentResponse(BaseModel):
    id: str
    title: str
    category: str
    tags: List[str]
    chunks: int
    filename: str
    uploaded_at: str
    uploader_id: str
    uploader_email: Optional[str] = None
    is_private: bool

@app.get("/documents", response_model=List[DocumentResponse])
def list_documents(current_user: User = Depends(get_current_user)):
    '''
        Eltárolt dokumentumok kilistázása a FileStore alapján (feltöltési dátummal és feltöltővel).
        Felhasználó: publikus + saját dokumentumok; adminisztrátor: az összes.
        Az indexelésben elbukott fájlok is szerepelnek (0 chunkkal).
    '''
    actor = Actor(user_id=current_user.id, role=current_user.role)
    chunk_counts = {d["id"]: d["chunks"] for d in kb.list_documents()}
    emails: dict[str, Optional[str]] = {}

    out: list[DocumentResponse] = []
    for stored in files.list_files(viewer=actor):
        if stored.uploader_id not in emails:
            uploader = auth_store.get_user_by_id(stored.uploader_id)
            emails[stored.uploader_id] = uploader.email if uploader else None
        out.append(DocumentResponse(
            id=stored.id,
            title=stored.name,
            category=stored.category,
            tags=list(stored.labels),
            chunks=chunk_counts.get(stored.index_id, 0) if stored.index_id else 0,
            filename=stored.original_filename,
            uploaded_at=stored.uploaded_at.isoformat(),
            uploader_id=stored.uploader_id,
            uploader_email=emails[stored.uploader_id],
            is_private=stored.is_private,
        ))
    return out

@app.get("/documents/{id}/download")
def download_document(id: str, current_user: User = Depends(get_current_user)):
    '''
        Az eredeti feltöltött fájl letöltése. Privát fájlt csak a feltöltő és az admin tölthet le.
    '''
    actor = Actor(user_id=current_user.id, role=current_user.role)
    stored = files.get(id, viewer=actor) or files.get_by_index_id(id, viewer=actor)
    if stored is None or not stored.path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nem található dokumentum a megadott azonosítóval: {id}"
        )
    return FileResponse(stored.path, filename=stored.original_filename)

@app.get("/admin/stats", response_model=SearchStatsResponse)
def search_stats(
    months: Annotated[int, Query(ge=1, le=120)] = DEFAULT_MONTHS,
    current_user: User = Depends(get_current_user)
):
    '''
        A leggyakrabban keresett dokumentumok és kategóriák (témák) havi bontásban.
        Egy dokumentum akkor számít keresettnek, ha szerepelt egy kérdés találatai között.
    '''
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="A statisztika csak adminisztrátornak érhető el.")

    def build(kind: Literal["document", "category"]) -> SearchStats:
        keys, counts = stats.monthly_counts(kind, months)
        titles = stats.last_titles() if kind == "document" else {}
        items: list[StatItem] = []
        for key, monthly in counts.items():
            if kind == "document":
                stored = files.get(key)
                label = stored.name if stored else f"{titles.get(key, key)} (törölve)"
                item_id = key
            else:
                label = key or "(kategória nélkül)"
                item_id = f"cat:{key}"
            items.append(StatItem(id=item_id, label=label, monthly=monthly))
        return SearchStats(months=keys, items=items)

    return SearchStatsResponse(documents=build("document"), categories=build("category"))

@app.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    '''
        WebSocket endpoint az LLM streaming kommunikációhoz.
    '''
    await websocket.accept()

    token = websocket.query_params.get("token") or websocket.cookies.get("session_token")
    user = auth_service.get_current_user(token) if token else None
    if user is None:
        await websocket.send_text(json.dumps({"type": "error", "message": "Bejelentkezés szükséges."}))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    viewer_id = user.id
    see_all = user.role == "admin"

    try:
        while True:
            user_query = await websocket.receive_text()

            if user_query.strip() == "__CLOSE__":
                await websocket.close()
                break

            # Üres bemenetek figyelmen kívül hagyása
            if not user_query.strip():
                continue

            query_id: Optional[int] = None
            answer_parts: list[str] = []
            try:
                # Keresés a felhasználó jogosultsági szintjével
                hits = kb.search(
                    query=user_query,
                    viewer_id=viewer_id,
                    see_all=see_all,
                )
                attach_file_ids(hits)
                query_id = log_query(viewer_id, "chat", user_query, hits)

                # Felhasznált források elküldése a kliensnek
                sources_payload = {
                    "type": "sources",
                    "sources": [
                        {
                            "title": h["title"],
                            "page": h["page"],
                            "doc_id": h["doc_id"],
                            "file_id": h["file_id"],
                            "score": h["score"]
                        } for h in hits ]
                }
                await websocket.send_text(json.dumps(sources_payload))

                # Válasz streamelése tokenenként
                async for token in stream_rag_response(user_query, hits):
                    answer_parts.append(token)
                    stream_payload = { "type": "token", "content": token }
                    await websocket.send_text(json.dumps(stream_payload))
                await websocket.send_text(json.dumps({"type": "end"}))
                record_answer(query_id, answer="".join(answer_parts))

            except WebSocketDisconnect:
                record_answer(query_id, answer="".join(answer_parts) or None, error="client disconnected")
                raise
            except Exception as err:
                record_answer(query_id, answer="".join(answer_parts) or None, error=str(err))
                # Ha belső hiba történik nem szakítjuk meg a Websocketet
                await websocket.send_text(json.dumps({"type": "error", "message": str(err)}))
    except WebSocketDisconnect:
        print("WebSocket kapcsolat bontva.")