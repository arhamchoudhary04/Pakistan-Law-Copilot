# First Steps

FastAPI is a modern, high-performance web framework for building APIs with Python,
based on standard Python type hints. It is built on top of Starlette (for the web
parts) and Pydantic (for the data parts).

## Creating an application

The simplest FastAPI application creates an instance of the `FastAPI` class and
declares a path operation with a decorator:

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}
```

The `app` variable is an instance of the class `FastAPI`. It is the main point of
interaction to create all your API.

## Running the server

You run the application with an ASGI server such as Uvicorn:

```
uvicorn main:app --reload
```

Here `main` is the Python module (the file `main.py`), `app` is the object created
inside `main.py`, and `--reload` makes the server restart after code changes. Use
`--reload` only during development, never in production.

## Path operations

A "path" is the part of the URL after the first `/`, also commonly called an
"endpoint" or a "route". An "operation" refers to an HTTP method: `POST`, `GET`,
`PUT`, `DELETE`, and the more exotic `OPTIONS`, `HEAD`, `PATCH`, `TRACE`.

You define path operations using decorators like `@app.get("/")`,
`@app.post("/")`, `@app.put("/")`, and `@app.delete("/")`. The function below the
decorator is called the "path operation function" and is called by FastAPI
whenever it receives a request to that URL using that method.

## Interactive API docs

FastAPI generates a "schema" of your API using the OpenAPI standard. Because of
this, it provides two interactive documentation interfaces out of the box:

- Swagger UI, served at `/docs`.
- ReDoc, served at `/redoc`.

The raw OpenAPI schema itself is served as JSON at `/openapi.json`.
