"""
Base Page Object with common methods for all pages.
"""

from playwright.async_api import Page, expect


class BasePage:
    """Base class for all page objects with common functionality."""

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

        # Common selectors
        self.flash_success = ".alert-success"
        self.flash_error = ".alert-error"

    def navigate(self, path: str = "/"):
        """Navigate to a path relative to base URL."""
        url = f"{self.base_url}{path}"
        self.page.goto(url, wait_until="domcontentloaded")
        return self

    def expect_success_flash(self, timeout: int = 5000):
        """Assert that a success flash message is displayed."""
        expect(self.page.locator(self.flash_success).first).to_be_visible(
            timeout=timeout
        )

    def expect_error_flash(self, timeout: int = 5000):
        """Assert that an error flash message is displayed."""
        expect(self.page.locator(self.flash_error).first).to_be_visible(timeout=timeout)
