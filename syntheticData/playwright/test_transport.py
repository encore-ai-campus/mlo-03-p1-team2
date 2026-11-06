"""Offline browser regression: no service/DB requests."""
import unittest
from playwright.async_api import async_playwright
from transport import OBSERVE_TRACKING, DRAIN_TRACKING


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_drain_waits_for_automatic_flush_before_python_route_starts(self):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page()
            await page.goto('data:text/html,<html>offline transport test</html>')
            # Reproduce a tracker timer that emptied its queue before a route callback.
            await page.evaluate('''() => {
                window.done = false;
                window.fetch = () => new Promise(resolve => setTimeout(() => {
                    window.done = true; resolve({ok: true});
                }, 150));
            }''')
            await page.evaluate(OBSERVE_TRACKING)
            await page.evaluate('() => { fetch("/api/v1/tracking/events"); }')
            await page.evaluate(DRAIN_TRACKING)
            self.assertTrue(await page.evaluate('window.done'))
            await browser.close()


if __name__ == '__main__':
    unittest.main()
