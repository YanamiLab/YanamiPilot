import asyncio
import base64
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from playwright.async_api import async_playwright
from browser_task_helper.adapters import zhihuishu as adapter
from browser_task_helper.config import Config
from browser_task_helper.demo import DemoServer
from browser_task_helper.runner import run
from browser_task_helper.runtime import Recovery, Reporter, write_json
from browser_task_helper.verification import VerificationBridge

class BrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.p=await async_playwright().start()
        self.browser=await self.p.chromium.launch(executable_path=os.environ.get('BROWSER_EXECUTABLE'),headless=True)
        self.page=await self.browser.new_page()

    async def asyncTearDown(self):
        await self.browser.close();await self.p.stop();self.temp.cleanup()

    async def test_hidden_verification_and_collapsed_chapter(self):
        await self.page.set_content('<div style="opacity:0">请完成安全验证</div><button onclick="document.querySelector(\'#rows\').style.display=\'block\'">第二章: Demo</button><div id="rows" style="display:none"><div class="item-box" onclick="this.dataset.clicked=1"><span class="item-num">2.1</span></div></div>')
        self.assertFalse(await adapter.visible_captcha(self.page))
        self.assertEqual(await adapter.select_lesson(self.page,self.page.locator('.item-box')),'2.1')
        self.assertEqual(await self.page.locator('.item-box').get_attribute('data-clicked'),'1')
        await self.page.set_content('<p>请完成安全验证</p>')
        self.assertTrue(await adapter.visible_captcha(self.page))

    async def test_loading_recovers_and_respects_retry_budget(self):
        calls=[]
        async def serve(route):
            calls.append(1)
            await route.fulfill(body='<p>loading</p>' if len(calls)==1 else '<div class="item-box">ready</div>',content_type='text/html')
        await self.page.route('https://fixture.test/',serve);await self.page.goto('https://fixture.test/')
        r=Recovery(90,1);image=self.root/'loading.png'
        self.assertEqual(await r.check(self.page,image,now=0),'waiting')
        self.assertEqual(await r.check(self.page,image,now=89),'waiting')
        self.assertEqual(len(calls),1)
        self.assertEqual(await r.check(self.page,image,now=90),'reloaded')
        self.assertEqual(await self.page.locator('.item-box').count(),1)
        self.assertEqual(await r.check(self.page,image,now=180),'failed')
        self.assertEqual(len(calls),2)
        r.progressed();self.assertEqual(r.attempts,0)

    async def test_challenge_requires_fresh_single_use_confirmation(self):
        svg='<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="gray"/></svg>'
        data=base64.b64encode(svg.encode()).decode()
        await self.page.set_content(f'<section id="challenge"><p>请完成安全验证</p><img alt="验证码背景" style="width:200px;height:200px" src="data:image/svg+xml;base64,{data}" onclick="this.parentElement.remove()"><button>请点击灰色大写A</button></section>')
        class FixtureBridge(VerificationBridge):
            calls=0
            async def solve_once(self,page,image,prompt_button,digest,prompt):
                self.calls+=1
                box=await image.bounding_box()
                await page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2)
                self.current['clicked_at']=time.time()
        bridge=FixtureBridge(self.root,Reporter(self.root),sys.executable)
        await bridge.handle(self.page,'1.1');token=bridge.current['id']
        self.assertEqual(bridge.calls,0)
        for grant in [{'id':'wrong','approved_at':time.time()},{'id':token,'approved_at':time.time()-121},{'id':token,'approved_at':time.time()+60}]:
            write_json(self.root/'approve-verification.json',grant)
            await bridge.handle(self.page,'1.1');self.assertEqual(bridge.calls,0)
            self.assertFalse((self.root/'approve-verification.json').exists())
        write_json(self.root/'approve-verification.json',{'id':token,'approved_at':time.time()})
        await bridge.handle(self.page,'1.1')
        self.assertEqual(bridge.calls,1)
        self.assertEqual(await self.page.locator('#challenge').count(),0)
        await bridge.cleared(self.page)
        await bridge.check_resumed(self.page,'1.1',{'time':1,'paused':False})
        self.assertFalse((self.root/'verification-result.json').exists())
        await bridge.check_resumed(self.page,'1.1',{'time':4,'paused':False})
        self.assertEqual(json.loads((self.root/'verification-result.json').read_text())['method'],'model')

    async def test_end_to_end_local_media_and_exercise(self):
        with DemoServer() as server:
            config=Config(url=server.url,expected_videos=2,state_dir=self.root/'run',headless=True,
                          executable_path=os.environ.get('BROWSER_EXECUTABLE'),poll_seconds=.3,
                          exercise_action='first_option')
            result=await asyncio.wait_for(run(config),90)
        self.assertEqual(result,0)
        status=json.loads((config.state_dir/'status.json').read_text())
        self.assertEqual(status['status'],'completed');self.assertEqual(status['confirmed'],2)
        events=[json.loads(line) for line in (config.state_dir/'events.jsonl').read_text().splitlines()]
        self.assertTrue(any(e['status']=='exercise_handled' for e in events))
        self.assertEqual({e['lesson'] for e in events if e['status']=='playing'},{'1.1','1.2'})
        self.assertTrue(all(e['speed']==1.5 for e in events if e['status']=='playing'))
