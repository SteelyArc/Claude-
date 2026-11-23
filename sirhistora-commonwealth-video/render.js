const {chromium}=require('playwright');const {spawn}=require('child_process');
const [,,a,b,out]=process.argv;const FPS=30;
(async()=>{
 const br=await chromium.launch();const p=await br.newPage({viewport:{width:1080,height:1920}});
 await p.goto('file://'+__dirname+'/video.html');await p.evaluate(()=>window.ready);
 const T=await p.evaluate(()=>window.TOTAL);const N=Math.ceil(T*FPS);
 const f0=Math.floor(N*a),f1=Math.floor(N*b);
 const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',''+FPS,'-c:v','mjpeg','-i','-','-c:v','libx264','-preset','medium','-crf','14','-pix_fmt','yuv420p',out],{stdio:['pipe','inherit','inherit']});
 const st=Date.now();
 for(let f=f0;f<f1;f++){await p.evaluate(t=>window.render(t),f/FPS);const buf=await p.screenshot({type:'jpeg',quality:95});
  if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));
  if((f-f0)%300===0)console.log(out,f-f0,'/',f1-f0,((Date.now()-st)/1000).toFixed(0)+'s');}
 ff.stdin.end();await new Promise(r=>ff.on('close',r));await br.close();console.log('done',out,N);
})();
