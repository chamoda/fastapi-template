#!/bin/env python

import asyncio
import inspect

from functools import wraps, partial
from typer import Typer

from app.database import AsyncSessionLocal
from app.models import User
from app.security import hash_password
from app.notifications import send_mail
from fastapi_mail import MessageSchema, MessageType


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
async def test_email(email: str):
    """Send a test email to verify email functionality."""
    try:
        message = MessageSchema(
            subject="Test Email from AlmaStack API",
            recipients=[email],
            body="This is a test email to verify that the email functionality is working correctly.\n\n"
            "If you received this email, the email system is configured properly.\n\n"
            "Thank you for using AlmaStack!",
            subtype=MessageType.plain,
        )

        await send_mail(message)
        print(f"✅ Test email sent successfully to {email}")
    except Exception as e:
        print(f"❌ Error sending test email: {e}")


if __name__ == "__main__":
    cli()
