const {chromium}=require('playwright');
(async()=>{
 const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
 const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
 await p.goto('file://'+__dirname+'/video.html');await p.evaluate(()=>window.ready);
 const T=await p.evaluate(()=>window.TOTAL);console.log('TOTAL',T.toFixed(1));
 let times=process.argv.slice(2).map(Number);
 if(process.argv[2]==='slides'){times=await p.evaluate(()=>window.SLIDE_MIDS)}
 for(const t of times){await p.evaluate(t=>window.render(t),t);await p.screenshot({path:`prev/f_${t.toFixed(1).padStart(6,'0')}.jpg`,type:'jpeg',quality:85});}
 console.log(times.map(t=>t.toFixed(1)).join(' '));
 console.log(errs.slice(0,5).join('\n'));await b.close();
})();
