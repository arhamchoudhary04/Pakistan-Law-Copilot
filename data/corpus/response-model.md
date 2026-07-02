# Response Model

You can declare the model used for the response with the `response_model`
parameter in any of the path operation decorators, such as `@app.get()` or
`@app.post()`.

## Declaring a response model

```python
from fastapi import FastAPI
from pydantic import BaseModel


class Item(BaseModel):
    name: str
    price: float
    tax: float | None = None


app = FastAPI()


@app.post("/items/", response_model=Item)
async def create_item(item: Item):
    return item
```

FastAPI will use the `response_model` to validate the returned data, convert and
filter the output data to the model's structure, add a JSON Schema for the
response in the OpenAPI path operation, and document the response in the automatic
docs.

## Filtering output data

The most important benefit is that `response_model` limits and filters the output
data to what is defined in the model. This is important for security: it prevents
accidentally returning sensitive data that is not part of the declared response.
For example, you can accept a user model that contains a password on input but
declare a separate response model without the password so the password is never
returned.

## response_model_exclude_unset

You can set the path operation decorator parameter `response_model_exclude_unset=True`
so that fields with default values that were not explicitly set are omitted from
the response. This is useful when your models have many optional fields and you
only want to return the values that were actually provided.

## Status codes

You can declare the HTTP status code used for the response with the `status_code`
parameter. It receives an integer (like `404`) or, preferably, one of the
constants from `fastapi.status`, such as `status.HTTP_201_CREATED`. The
`status_code` is used in the response and added to the OpenAPI schema.
