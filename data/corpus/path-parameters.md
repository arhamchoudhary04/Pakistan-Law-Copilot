# Path Parameters

You can declare path "parameters" or "variables" with the same syntax used by
Python format strings.

## Declaring a path parameter

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/items/{item_id}")
async def read_item(item_id):
    return {"item_id": item_id}
```

The value of the path parameter `item_id` is passed to your function as the
argument `item_id`.

## Path parameters with types

You can declare the type of a path parameter in the function using standard Python
type annotations:

```python
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
```

Here `item_id` is declared to be an `int`. This gives editor support and, more
importantly, "parsing": the string coming from the request is converted to an
`int`. If you pass a value that is not a valid `int`, FastAPI returns an HTTP 422
error with a clear JSON description of the error. This data validation is provided
by Pydantic.

## Order matters

When creating path operations, fixed paths can conflict with paths that use
parameters. Because path operations are evaluated in order, you need to declare
the fixed path `/users/me` before the variable path `/users/{user_id}`, otherwise
the variable path would also match `/users/me`, thinking that it is receiving a
`user_id` with the value `"me"`.

## Predefined values with Enum

If you have a path operation that receives a path parameter but you want the
possible valid values to be predefined, you can use a standard Python `Enum`.
Import `Enum` and create a subclass that also inherits from `str`, so the API docs
know the values must be strings and render correctly.

## Path parameters containing paths

Using an option directly from Starlette you can declare a path parameter
containing a path with the URL syntax `/files/{file_path:path}`. The `:path` part
tells the framework that the parameter should match any path.
