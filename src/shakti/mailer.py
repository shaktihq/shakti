"""Email sending — send emails in 2 lines.

Usage::

    from shakti.mailer import Mailer

    mailer = Mailer(config)
    mailer.init_app(app)

    # Send email anywhere
    await mailer.send(
        to="user@example.com",
        subject="Welcome!",
        body="Thanks for joining.",
    )

    # HTML email
    await mailer.send(
        to="user@example.com",
        subject="Welcome!",
        body="Thanks for joining.",
        html="<h1>Thanks for joining!</h1>",
    )
"""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shakti.application import Shakti
    from shakti.config.settings import Config


class Mailer:
    """Async email sender using SMTP.

    Config keys (under ``mail:``):

    .. code-block:: yaml

        mail:
          host: smtp.gmail.com
          port: 587
          username: you@gmail.com
          password: ${MAIL_PASSWORD}
          from: "My App <you@gmail.com>"
          use_tls: true
    """

    def __init__(
        self,
        config: Config | None = None,
        *,
        host: str = "localhost",
        port: int = 587,
        username: str = "",
        password: str = "",
        from_address: str = "",
        use_tls: bool = True,
        use_ssl: bool = False,
    ) -> None:
        if config is not None:
            host         = config.get("mail.host", host)
            port         = config.get("mail.port", port, cast=int)
            username     = config.get("mail.username", username)
            password     = config.get("mail.password", password)
            from_address = config.get("mail.from", from_address or username)
            use_tls      = config.get("mail.use_tls", use_tls, cast=bool)
            use_ssl      = config.get("mail.use_ssl", use_ssl, cast=bool)

        self.host         = host
        self.port         = port
        self.username     = username
        self.password     = password
        self.from_address = from_address or username
        self.use_tls      = use_tls
        self.use_ssl      = use_ssl

    def init_app(self, app: Shakti) -> None:
        app.container.register_instance(Mailer, self)

    async def send(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        *,
        html: str | None = None,
        from_address: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> None:
        """Send an email. Runs in a thread pool to avoid blocking."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._send_sync, to, subject, body, html, from_address, cc, bcc
        )

    def _send_sync(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        html: str | None,
        from_address: str | None,
        cc: list[str] | None,
        bcc: list[str] | None,
    ) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = from_address or self.from_address
        msg["To"]      = to if isinstance(to, str) else ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)

        msg.attach(MIMEText(body, "plain"))
        if html:
            msg.attach(MIMEText(html, "html"))

        recipients = ([to] if isinstance(to, str) else to) + (cc or []) + (bcc or [])

        if self.use_ssl:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.host, self.port, context=ctx) as server:
                if self.username:
                    server.login(self.username, self.password)
                server.send_message(msg, to_addrs=recipients)
        else:
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username:
                    server.login(self.username, self.password)
                server.send_message(msg, to_addrs=recipients)

    def __repr__(self) -> str:
        return f"<Mailer host={self.host!r} port={self.port}>"
