import re

async def visibly_exposed(item):
    if not await item.is_visible():
        return False
    return await item.evaluate("""e => {
        for(let n=e;n;n=n.parentElement){const s=getComputedStyle(n);
            if(s.visibility==='hidden'||s.display==='none'||Number(s.opacity)===0)return false;}
        const r=e.getBoundingClientRect();
        const x=Math.max(0,Math.min(innerWidth-1,r.x+r.width/2));
        const y=Math.max(0,Math.min(innerHeight-1,r.y+r.height/2));
        const top=document.elementFromPoint(x,y);
        return r.width>5&&r.height>5&&!!top&&(top===e||e.contains(top));
    }""")

async def visible_captcha(page):
    for item in await page.get_by_text('请完成安全验证', exact=True).all():
        if await visibly_exposed(item):
            return True
    for item in await page.locator('iframe[src*="captcha"]').all():
        if not await visibly_exposed(item):
            continue
        handle = await item.element_handle()
        frame = await handle.content_frame()
        if frame:
            for text in ('安全验证', '拖动下方滑块完成拼图'):
                for label in await frame.get_by_text(text, exact=True).all():
                    if await label.is_visible():
                        return True
    return False

async def exercise(page):
    dialog = page.locator('.ai-class-exercise-dialog:visible')
    if not await dialog.count():
        return False
    # Scope every selector to the ungraded in-video dialog, never chapter tests.
    if not await dialog.get_by_text('正确答案', exact=False).count():
        for question in await dialog.locator('.ques-list .item').all():
            options = question.locator('.option')
            if await options.count():
                await options.first.click()
        submit = dialog.get_by_role('button', name='提交作答', exact=True)
        if await submit.count() and await submit.is_enabled():
            await submit.click()
            await page.wait_for_timeout(500)
    if await dialog.count():
        close = dialog.locator('.header-icon')
        if await close.count():
            await close.click()
    return True

async def select_lesson(page, row):
    number = (await row.locator('.item-num').text_content()).strip()
    if not await row.is_visible():
        chapter = int(number.split('.')[0])
        name = '第' + '一二三四五六七八九十'[chapter-1] + '章'
        header = page.get_by_role('button', name=re.compile('^'+name))
        await header.click()
        await row.wait_for(state='visible')
    await row.click()
    return number

async def ensure_rate(page, video, speed=1.5):
    actual = await video.evaluate('e=>e.playbackRate')
    label = page.locator('#vjs_container .speedBox > span')
    ui = await label.text_content() if await label.count() else None
    if actual != speed or (ui is not None and str(speed) not in ui):
        choice = page.locator(f'#vjs_container .speedTab[rate="{speed}"]')
        if await choice.count():
            await page.locator('#vjs_container').hover()
            await page.locator('#vjs_container .speedBox').hover()
            await choice.click()
        else:
            await video.evaluate('(e, speed)=>{e.playbackRate=speed}', speed)
    return {'actual':await video.evaluate('e=>e.playbackRate'),
            'label':await label.text_content() if await label.count() else None}
