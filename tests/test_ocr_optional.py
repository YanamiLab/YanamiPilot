import base64
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from playwright.async_api import async_playwright
from browser_task_helper.verification import VerificationBridge
from browser_task_helper.runtime import Reporter, write_json

@unittest.skipUnless(os.environ.get('OCR_PYTHON'), 'Optional local OCR environment not configured')
class OCRTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_models_and_scaled_browser_click_on_original_fixture(self):
        svg='<svg xmlns="http://www.w3.org/2000/svg" width="400" height="160"><rect width="400" height="160" fill="#eeeeee"/><text x="30" y="110" font-family="Arial" font-size="85" fill="#888888">N</text><text x="160" y="110" font-family="Arial" font-size="85" fill="#888888">A</text><text x="290" y="110" font-family="Arial" font-size="85" fill="red">A</text></svg>'
        image='data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()
        html=f'<div id="challenge"><p>请完成安全验证</p><img alt="验证码背景" src="{image}" style="width:600px;height:240px" onclick="if(event.offsetX>230 &amp;&amp; event.offsetX&lt;350) this.parentElement.remove()"><button>请点击灰色大写A</button></div>'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            async with async_playwright() as p:
                browser=await p.chromium.launch(executable_path=os.environ.get('BROWSER_EXECUTABLE'),headless=True)
                try:
                    page=await browser.new_page();await page.set_content(html)
                    bridge=VerificationBridge(root,Reporter(root),os.environ['OCR_PYTHON'])
                    await bridge.handle(page,'fixture')
                    self.assertFalse((root/'prediction.json').exists())
                    write_json(root/'approve-verification.json',dict(id=bridge.current['id'],approved_at=time.time()))
                    await bridge.handle(page,'fixture')
                    self.assertEqual(bridge.current['stage'],'clicked_waiting_for_acceptance')
                    self.assertEqual(await page.locator('#challenge').count(),0)
                    self.assertEqual(json.loads((root/'prediction.json').read_text())['status'],'ready')
                finally:await browser.close()
