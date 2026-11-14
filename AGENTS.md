# Requirements Specification

## Document-based Knowledge Base and Question-Answer System

**Task Description**

The task is to create a document-based knowledge base management system where users can upload various documents and then ask natural language questions about the content of those documents.

**Detailed Task Description**

The goal of the project is to create a knowledge base that supports multiple document formats such as PDF, text documents, and images.

Registration of a new document works as follows:

- After uploading, the system attempts to automatically extract the textual content of the document
- If a document does not contain machine-readable text, the system performs OCR processing
- The system splits processed documents into searchable chunks
- Data is stored in a way that allows it to be retrieved later based on relevance

Each document is associated with a title, category, upload date, uploader, and optional tags.

The system includes full-text search allowing keyword-based searches across documents. Additionally, users can perform semantic searches to find relevant document sections even when they do not use the exact same terms as in the documents. Furthermore, the goal is for users to be able to ask questions in natural language about the knowledge base content.

Answer generation for asked questions works as follows:

- The system finds the most relevant document sections for the question
- Based on these, an LLM generates a response
- Alongside the answer, the documents and page numbers or text excerpts used to compose the response are displayed
- The system logs all asked questions and their corresponding answers

The administrative interface shows which documents and topics are most frequently searched by users. Uploading new documents, searching, and writing prompts require authentication.

### Technical Parameters

The application has two main layers: the **frontend** and the **backend**. The backend is a **Python application** providing **FastAPI** endpoints for searching, adding, and deleting documents. A **ChromaDB** vector database stores **document chunks** and their **metadata**, with embeddings produced by a **Sentence Transformer** model. Full documents are placed in a separate **file storage**, and their titles and locations are stored in chunk metadata. Allowed formats are **text files** (.txt, .md), **PDF documents**, or **rasterized images** (.jpg, .png, .webp). Queries use **cosine similarity** to determine the **top 10** most relevant text segments, which are then **reranked** using **BM25** and **fuzzy matching**, returning the **top 5** text segments. If a chunk's relevance falls below the **relevance threshold**, it is **discarded**. The backend provides a **websocket endpoint** for communicating with the LLM. An incoming user prompt gets a general **system prompt** prepended, and the LLM's response is forwarded to the frontend.

The frontend is a simple **React application** providing document **management** and **searching** between documents. The interface requires **authentication** with two roles: **user** and **administrator**. Users can **search** among files, **list** all files, and **download** them. Administrators have access to the **admin panel** and can **edit files**. The interface allows selecting an **OpenAI API**-**compatible endpoint**, which is forwarded to the backend for LLM communication. When searching, the frontend **queries** the backend for relevant documents, and if the user selected chat mode, it **forwards** the query to the backend's LLM websocket, which **streams** its response to the UI.
