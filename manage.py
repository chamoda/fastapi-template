#!/bin/env python

import asyncio
import inspect

from functools import wraps, partial
from typer import Typer
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import User
from app.secuirty import hash_password


class AsyncTyper(Typer):
    @staticmethod
    def maybe_run_async(decorator, f):
        if inspect.iscoroutinefunction(f):

            @wraps(f)
            def runner(*args, **kwargs):
                return asyncio.run(f(*args, **kwargs))

            decorator(runner)
        else:
            decorator(f)
        return f

    def callback(self, *args, **kwargs):
        decorator = super().callback(*args, **kwargs)
        return partial(self.maybe_run_async, decorator)

    def command(self, *args, **kwargs):
        decorator = super().command(*args, **kwargs)
        return partial(self.maybe_run_async, decorator)


session = AsyncSessionLocal()
cli = AsyncTyper()


@cli.command()
async def create_user(
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    is_admin: bool,
):
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=hash_password(password),
        is_admin=is_admin,
    )
    session.add(user)
    await session.commit()
    print("User created: ", user.id)


@cli.command()
async def make_admin(email: str):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        print("User not found")
        return
    user.is_admin = True
    await session.commit()


if __name__ == "__main__":
    cli()
