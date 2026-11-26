const { chromium } = require('playwright');
const fs = require('fs'), path=require('path'), { spawn } = require('child_process');
(async()=>{
  const mouth = JSON.parse(fs.readFileSync('mouth.json'));
  const N = mouth.length;
  const b = await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p = await b.newPage({viewport:{width:1080,height:1920}});
  await p.route('**/three.min.js', r=>r.fulfill({path: path.resolve('n/node_modules/three/build/three.min.js'), contentType:'application/javascript'}));
  await p.goto('file://'+path.resolve('guara.html')+'#render');
  await p.waitForFunction(()=>window.renderAt);
  await p.evaluate(()=>setGestures([[0.0,1.7],[12.6,13.6],[23.3,26.2]]));
  const ff = spawn('ffmpeg',['-v','error','-y','-f','image2pipe','-framerate','30','-c:v','mjpeg','-i','-','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','frames.mp4'],{stdio:['pipe','inherit','inherit']});
  for (let i=0;i<N;i++){
    const d = await p.evaluate(([t,m])=>{renderAt(t,m);return document.querySelector('canvas').toDataURL('image/jpeg',0.93)},[i/30, mouth[i]]);
    if (!ff.stdin.write(Buffer.from(d.split(',')[1],'base64'))) await new Promise(r=>ff.stdin.once('drain',r));
    if (i%200==0) console.log(i,'/',N);
  }
  ff.stdin.end(); await new Promise(r=>ff.on('close',r)); await b.close();
})();
