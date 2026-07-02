# Request Body

When you need to send data from a client to your API, you send it as a request
body. To declare a request body you use Pydantic models.

## Declaring a body with a Pydantic model

```python
from fastapi import FastAPI
from pydantic import BaseModel


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None


app = FastAPI()


@app.post("/items/")
async def create_item(item: Item):
    return item
```

To add a request body, declare it as a function parameter and type it with a
Pydantic model. The same model gives you data validation, editor support, and
automatic documentation.

## What FastAPI does with the model

With that declaration, FastAPI reads the body of the request as JSON, converts the
types if needed, validates the data, and gives you the received data in the
parameter `item`. If the data is invalid, it returns a clear error indicating
exactly where and what the incorrect data was. It also generates JSON Schema
definitions for your model that are included in the OpenAPI schema and used by the
docs.

## Request body plus path and query parameters

You can declare path parameters, query parameters, and a request body at the same
time, and FastAPI will recognize each correctly. The function parameters are
recognized as follows:

- If the parameter is also declared in the path, it is a path parameter.
- If the parameter is of a singular type (like `int`, `float`, `str`, `bool`) it
  is interpreted as a query parameter.
- If the parameter is declared to be the type of a Pydantic model, it is
  interpreted as a request body.

## Multiple body parameters

You can declare multiple body parameters, for example two Pydantic models. FastAPI
will expect a JSON body with each model's data under a key named after the
parameter. You can also use the `Body` function to declare singular values as part
of the body rather than as query parameters.
