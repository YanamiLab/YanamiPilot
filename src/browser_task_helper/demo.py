"""Original local fixture. No real course pages, users, or verification images."""
import asyncio
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import Config
from .runner import run

HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8">
<title>YanamiPilot — local demo</title>
<style>body{background:#101526;color:#e5edf9;font:18px system-ui;margin:3rem}button,.item-box{cursor:pointer;padding:12px;margin:8px;border:1px solid #617dad;border-radius:10px}.finish-icon{color:#81e6ad}video{width:480px}canvas{display:none}.ai-class-exercise-dialog{display:none;background:#273451;padding:24px}.speedBox{padding:10px}</style>
<h1>YanamiPilot · 续航</h1><p>Local demo: real generated media → practice dialog → next video → verified completion.</p>
<button>第一章: Demo</button><section id="catalog"></section>
<div id="vjs_container"><video muted></video><div class="speedBox"><span>X 1</span><button class="speedTab" rate="1.5" onclick="document.querySelector('video').playbackRate=1.5;document.querySelector('.speedBox > span').textContent='X 1.5'">1.5×</button></div></div>
<div class="ai-class-exercise-dialog"><h2>AI随堂练习 · local fixture</h2><div class="ques-list"><div class="item"><div class="option" onclick="this.dataset.selected='true'">A: sample answer</div></div></div><button onclick="document.querySelector('.ai-class-exercise-dialog').insertAdjacentHTML('beforeend','<p>正确答案：A</p>')">提交作答</button><button class="header-icon" onclick="this.parentElement.style.display='none'">Close</button></div>
<canvas width="480" height="240"></canvas>
<script>
const catalog=document.querySelector('#catalog');let current=null,clip=null,shown=false;
for(let i=1;i<=2;i++){const row=document.createElement('div');row.className='item-box';row.innerHTML=`<span class="item-num">1.${i}</span> Local video ${i} `+(localStorage.getItem('done'+i)?'<span class="finish-icon">✓</span>':'');row.onclick=()=>start(i);catalog.append(row)}
const video=document.querySelector('video'),canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d');
setInterval(()=>{ctx.fillStyle='#193455';ctx.fillRect(0,0,480,240);ctx.fillStyle='#b1f0df';ctx.font='24px sans-serif';ctx.fillText('Local browser demo '+Date.now()%100000,24,120)},80);
const ready=(async()=>{const stream=canvas.captureStream(12),rec=new MediaRecorder(stream),chunks=[];rec.ondataavailable=e=>chunks.push(e.data);const ended=new Promise(r=>rec.onstop=r);rec.start();await new Promise(r=>setTimeout(r,4500));rec.stop();await ended;stream.getTracks().forEach(t=>t.stop());clip=URL.createObjectURL(new Blob(chunks,{type:rec.mimeType}))})();
async function start(i){await ready;current=i;shown=false;video.src=clip;await video.play()}
video.addEventListener('timeupdate',()=>{if(current===1&&!shown&&video.currentTime>1){shown=true;video.pause();document.querySelector('.ai-class-exercise-dialog').style.display='block'}});
video.addEventListener('ended',()=>{localStorage.setItem('done'+current,'1');const row=catalog.children[current-1];if(!row.querySelector('.finish-icon'))row.insertAdjacentHTML('beforeend','<span class="finish-icon">✓</span>')});
</script></html>'''


class DemoServer:
    def __enter__(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/"
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


async def main():
    # Headless demo for CI and new users; real sessions default to visible windows.
    with tempfile.TemporaryDirectory(prefix="yanamipilot-demo-") as directory, DemoServer() as server:
        config = Config(url=server.url, expected_videos=2, state_dir=Path(directory),
                        executable_path=os.environ.get("BROWSER_EXECUTABLE"), headless=True,
                        poll_seconds=0.3, exercise_action="first_option", load_timeout=15)
        result = await asyncio.wait_for(run(config), timeout=90)
        if result:
            raise RuntimeError("Local demo failed")
        print("Local demo completed. Temporary profile, media and server cleaned up.")
        return result
