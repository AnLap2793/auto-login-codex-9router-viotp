import re

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError


async def first_visible(*locators: Locator, timeout: int = 1_500) -> Locator | None:
    for locator in locators:
        try:
            await locator.first.wait_for(state="visible", timeout=timeout)
            return locator.first
        except PlaywrightTimeoutError:
            continue
    return None


async def email_input(page: Page, timeout: int = 1_500) -> Locator | None:
    return await first_visible(
        page.get_by_label(re.compile(r"email", re.I)),
        page.locator('input[name="username"]'),
        page.locator('input[type="email"]'),
        timeout=timeout,
    )


async def password_input(page: Page, timeout: int = 1_500) -> Locator | None:
    return await first_visible(
        page.get_by_label(re.compile(r"password", re.I)),
        page.locator('input[name="password"]'),
        page.locator('input[type="password"]'),
        timeout=timeout,
    )


async def otp_input(page: Page, timeout: int = 1_500) -> Locator | None:
    return await first_visible(
        page.get_by_label(re.compile(r"(code|verification)", re.I)),
        page.locator('input[autocomplete="one-time-code"]'),
        page.locator('input[name="code"]'),
        timeout=timeout,
    )


async def visible_error_text(page: Page) -> str:
    candidates = page.locator('[role="alert"], [aria-live="assertive"], [aria-live="polite"]')
    texts: list[str] = []
    for index in range(min(await candidates.count(), 10)):
        candidate = candidates.nth(index)
        if await candidate.is_visible():
            text = (await candidate.inner_text()).strip()
            if text:
                texts.append(text[:500])
    return " ".join(texts)


async def blocker(page: Page) -> str | None:
    url = page.url.lower()
    body = (await page.locator("body").inner_text(timeout=2_000)).lower()
    if await page.locator('input[type="tel"]').count() or "phone verification" in body:
        return "phone"
    if "captcha" in url or "challenge" in url or "verify you are human" in body:
        return "captcha"
    return None
