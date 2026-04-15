import requests

url = "http://localhost:8000/generate"

payload = {
    "raw_notes":""" Pydantic Models-  **Request Models:** Define the structure and validation rules for incoming request bodies (e.g., `POST` data).- **Response Models:** Define the structure of the data returned by path operations, automatically serializing Python objects to JSON and filtering fields.
- **Database Models:** (Often ORM-specific) Represent the structure of your database tables. These are often distinct from your request/response models to decouple your API from your database schema.
**Dependency Injection System:** FastAPI's powerful mechanism for managing shared resources (like database connections), authentication, authorization, and other common functionalities. Dependencies are simply functions that “inject” into your path operations.
**Routers (**`**APIRouter**`**):** A way to organize path operations into logical groups (e.g., all user-related endpoints, all document-related endpoints). This prevents `main.py` from becoming a monolithic file.
**Database Interaction:** Code that connects to your database, performs queries, and manages sessions (e.g., using `SQLAlchemy`, `Tortoise ORM`, or raw `psycopg2`).
**Configuration Management:** Handling environment variables, settings, and secrets.
**Error Handling:** Custom exception handlers for specific error conditions.
**Static Files & Templates:** (Less common for pure APIs, but possible) Serving static content or dynamic HTML.""",
    "platforms" : ["blog"],
    "author_name": "Your Name",
    "style": "dhruv_default",
    "extra_material": ""
}

response = requests.post(url, json=payload)
print("Status Code:", response.status_code)
print("Response:", response.json())
