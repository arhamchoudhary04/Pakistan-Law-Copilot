# Handling Errors

There are many situations in which you need to notify a client that something went
wrong: the client does not have permission, has no access to a resource, or the
item does not exist. In these cases you normally return an HTTP status code in the
range of 400 (from 400 to 499).

## Using HTTPException

To return HTTP responses with errors to the client you use `HTTPException`:

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

items = {"foo": "The Foo Wrestlers"}


@app.get("/items/{item_id}")
async def read_item(item_id: str):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": items[item_id]}
```

`HTTPException` is a normal Python exception with additional data relevant for
APIs. Because it is a Python exception, you `raise` it, you do not `return` it.
When raised, the rest of the code in the path operation is not executed, and the
request is terminated immediately with the given error.

## Adding custom headers

You can add custom headers to the error response by passing the `headers`
parameter to `HTTPException`. This is useful in some advanced scenarios, for
example certain types of security.

## Custom exception handlers

You can add custom exception handlers with the same exception utilities from
Starlette. Suppose you have a custom exception `UnicornException`. You register a
handler with the `@app.exception_handler()` decorator, and when a request raises
that exception, FastAPI calls your handler to build the response.

## Overriding validation errors

When a request contains invalid data, FastAPI raises a `RequestValidationError`
internally and returns an HTTP 422 response by default. You can override the
default handler for `RequestValidationError` to customize the body returned for
validation errors, for example to log the invalid payload.
