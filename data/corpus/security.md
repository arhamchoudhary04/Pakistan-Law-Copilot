# Security

FastAPI provides several tools to help you deal with security easily, rapidly, in
a standard way, without having to study and learn all the security
specifications. It has built-in support for OAuth2, API keys, and HTTP
authentication schemes.

## OAuth2 with Password and Bearer

A common flow is OAuth2 with the "password" flow using a Bearer token. FastAPI
provides `OAuth2PasswordBearer` for this. You create an instance passing the
`tokenUrl`, which is the relative URL where the client will send the username and
password to get a token:

```python
from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/items/")
async def read_items(token: str = Depends(oauth2_scheme)):
    return {"token": token}
```

The `oauth2_scheme` is a dependency. When a request arrives, FastAPI checks the
request's `Authorization` header for a Bearer token, extracts it, and passes it to
your function as `token`. If there is no token, it returns an HTTP 401 error.

## Getting the current user

You typically write a dependency `get_current_user` that receives the token,
decodes and verifies it, and returns the corresponding user. Path operations then
depend on `get_current_user`, so any protected endpoint simply declares it and
receives the authenticated user.

## Hashing passwords

You should never store plaintext passwords. FastAPI's security tutorial recommends
hashing passwords using a library such as `passlib`, storing only the hash, and
verifying a login attempt by hashing the provided password and comparing it to the
stored hash.

## JWT tokens

For real applications, tokens are commonly JSON Web Tokens (JWT). A JWT is signed
so the server can verify it was not tampered with. You generate a token at login
with an expiration time, and `get_current_user` decodes and validates the JWT on
each request, rejecting expired or invalid tokens with an HTTP 401 error.

## Scopes

OAuth2 has the notion of "scopes" — extra permissions that can be attached to a
token. FastAPI provides `SecurityScopes` and the `Security` function so you can
declare and require specific scopes per path operation.
