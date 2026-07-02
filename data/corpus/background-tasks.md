# Background Tasks

You can define background tasks to be run after returning a response. This is
useful for operations that need to happen after a request, but that the client
does not need to wait for before receiving the response.

## Using BackgroundTasks

You declare a parameter of type `BackgroundTasks` in your path operation function,
and FastAPI creates and passes the object for you:

```python
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()


def write_notification(email: str, message: str = ""):
    with open("log.txt", mode="a") as email_file:
        email_file.write(f"notification for {email}: {message}")


@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(write_notification, email, message="some notification")
    return {"message": "Notification sent in the background"}
```

You add tasks with `background_tasks.add_task()`, passing the task function
followed by any positional and keyword arguments. The task runs after the
response is sent.

## Examples of use cases

Background tasks are useful for things like sending email notifications after
performing an action, or processing data: for example a request could receive a
file that must go through a slow process, and you can return a "Accepted" response
and do the processing in the background.

## Background tasks and dependencies

`BackgroundTasks` also works with the dependency injection system. You can declare
a parameter of type `BackgroundTasks` at multiple levels — in a path operation
function, in a dependency, and so on — and FastAPI knows how to combine them and
run all of the added tasks.

## Caveat: heavy computation

If you need to perform heavy background computation and you do not necessarily need
it to run in the same process (for example, you do not need to share memory,
variables, etc.), you might benefit from using a bigger tool like Celery instead.
`BackgroundTasks` runs in the same event loop, so CPU-heavy work can block it.
