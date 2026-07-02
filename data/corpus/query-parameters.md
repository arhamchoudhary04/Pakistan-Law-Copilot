# Query Parameters

When you declare function parameters that are not part of the path parameters,
they are automatically interpreted as "query" parameters.

## Declaring query parameters

```python
from fastapi import FastAPI

app = FastAPI()

fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]


@app.get("/items/")
async def read_item(skip: int = 0, limit: int = 10):
    return fake_items_db[skip : skip + limit]
```

The query is the set of key-value pairs that go after the `?` in a URL, separated
by `&` characters. For example, in `http://127.0.0.1:8000/items/?skip=0&limit=10`
the query parameters are `skip` (value `0`) and `limit` (value `10`).

## Defaults

Because query parameters are not a fixed part of a path, they can be optional and
can have default values. In the example above, `skip` has a default value of `0`
and `limit` a default of `10`, so going to `/items/` is the same as going to
`/items/?skip=0&limit=10`.

## Optional parameters

You can declare optional query parameters by setting their default to `None`:

```python
@app.get("/items/{item_id}")
async def read_item(item_id: str, q: str | None = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}
```

Here `q` is optional and defaults to `None`. FastAPI knows `q` is not required
because of the default value.

## Required query parameters

When you want to make a query parameter required, do not declare any default
value. If you want to declare it as required while still allowing `None` as a
value, do not give it a default. If you declare a default value, the parameter is
not required.

## Type conversion for booleans

Query parameters are always strings in the raw request, but when you declare them
with a Python type they are converted. For a `bool` type, values like `1`, `True`,
`true`, `on`, and `yes` are converted to `True` (case-insensitive).
