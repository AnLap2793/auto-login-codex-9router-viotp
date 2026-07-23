import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .accounts import Account, parse_accounts
from .cancellation import CancellationToken
from .config import normalize_host

if TYPE_CHECKING:
    from .auth.automation import AccountResult


@dataclass(frozen=True, slots=True)
class StatusUpdate:
    line_number: int
    masked_email: str
    status: str
    detail: str = ""


StatusCallback = Callable[[StatusUpdate], None]


def _emit(callback: StatusCallback | None, update: StatusUpdate) -> None:
    if callback:
        callback(update)


async def run_text(
    text: str,
    host: str,
    on_status: StatusCallback | None = None,
    cancellation: CancellationToken | None = None,
    dashboard_password: str | None = None,
    headless: bool = False,
) -> list["AccountResult"]:
    host = normalize_host(host)
    cancellation = cancellation or CancellationToken()
    accounts, errors = parse_accounts(text)
    for error in errors:
        _emit(on_status, StatusUpdate(error.line_number, "—", "failed", error.message))
    for account in accounts:
        _emit(on_status, StatusUpdate(account.line_number, account.masked_email, "pending"))
    if not accounts:
        return []

    from playwright.async_api import async_playwright

    from .auth.automation import AccountResult, run_account
    from .integrations.oauth_callback import CallbackServer

    async def run_one(account: Account) -> AccountResult:
        if cancellation.cancelled:
            result = AccountResult(account, "cancelled", "đã dừng theo yêu cầu")
        else:
            _emit(on_status, StatusUpdate(account.line_number, account.masked_email, "running"))
            result = await run_account(
                playwright,
                account,
                host,
                callback_server,
                cancellation,
                dashboard_password,
                headless,
            )
        _emit(on_status, StatusUpdate(account.line_number, account.masked_email, result.code, result.detail))
        return result

    with CallbackServer() as callback_server:
        async with async_playwright() as playwright:
            tasks = [asyncio.create_task(run_one(account)) for account in accounts]
            while not all(task.done() for task in tasks):
                if cancellation.cancelled:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    break
                await asyncio.sleep(0.1)
            results = await asyncio.gather(*tasks, return_exceptions=True)

    finalized: list[AccountResult] = []
    for account, result in zip(accounts, results, strict=True):
        if isinstance(result, BaseException):
            result = AccountResult(account, "cancelled", "đã dừng theo yêu cầu")
            _emit(on_status, StatusUpdate(account.line_number, account.masked_email, result.code, result.detail))
        finalized.append(result)
    return finalized
