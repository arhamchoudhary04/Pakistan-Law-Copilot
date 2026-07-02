# Dependencies

FastAPI has a very powerful but intuitive Dependency Injection system. It is
designed to be simple to use and to make it easy for any developer to integrate
other components with FastAPI.

## What is a dependency

A "dependency" is just a function that can take all the same parameters that a
path operation function can take:

```python
from fastapi import Depends, FastAPI

app = FastAPI()


async def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}


@app.get("/items/")
async def read_items(commons: dict = Depends(common_parameters)):
    return commons
```

You declare a dependency in a path operation function with `Depends()`. FastAPI
calls the dependency function, passing it the parameters from the request, and
gives the result to your path operation.

## Why use dependencies

Dependencies are useful for shared logic, database connections, enforcing
security and authentication, and many other things. They minimize code repetition
because the same dependency can be reused across many path operations.

## Classes as dependencies

You can also use a class as a dependency. FastAPI inspects the class's `__init__`
method the same way it inspects a function's parameters. When you use a class,
FastAPI knows the type of the resulting value, giving you better editor support.

## Dependencies with yield

FastAPI supports dependencies that do some steps before returning a value and
additional steps after the response is delivered, using `yield` instead of
`return`. This is commonly used to manage resources such as database sessions: the
code before the `yield` runs before sending the response, the yielded value is
injected, and the code after the `yield` runs after the response is sent, even if
there was an exception.

## Global dependencies

For some applications you might want to add dependencies to the whole application.
You can add them to the `FastAPI` app with the `dependencies` parameter, so they
are applied to every path operation.
