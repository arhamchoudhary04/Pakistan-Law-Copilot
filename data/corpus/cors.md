# CORS (Cross-Origin Resource Sharing)

CORS refers to the situations when a frontend running in a browser has JavaScript
code that communicates with a backend, and the backend is in a different "origin"
than the frontend.

## What is an origin

An origin is the combination of protocol (`http`, `https`), domain
(`myapp.com`, `localhost`), and port (`80`, `443`, `8080`). So all of these are
different origins: `http://localhost`, `https://localhost`, and
`http://localhost:8080`. Even though they are all `localhost`, they use different
protocols or ports, so they are different origins.

## Why CORS matters

Browsers enforce a same-origin policy. If a frontend at `http://localhost:8080`
tries to call a backend at `http://localhost:8000`, the browser will block the
request unless the backend explicitly permits the frontend's origin using CORS
headers.

## Using CORSMiddleware

You can configure CORS in FastAPI using `CORSMiddleware`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

You import `CORSMiddleware`, create a list of allowed origins as strings, and add
it to your application with `app.add_middleware()`.

## Middleware parameters

`CORSMiddleware` supports several arguments:

- `allow_origins`: a list of origins that are allowed to make cross-origin
  requests. You can use `["*"]` to allow any origin.
- `allow_methods`: a list of HTTP methods allowed for cross-origin requests. Use
  `["*"]` to allow all standard methods.
- `allow_headers`: a list of HTTP request headers that are supported. Use `["*"]`
  to allow all headers.
- `allow_credentials`: whether cookies should be supported for cross-origin
  requests. When this is `True`, `allow_origins` cannot be set to `["*"]`; you
  must specify explicit origins.
