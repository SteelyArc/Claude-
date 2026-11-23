const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+__dirname+'/video.html');
console.log(JSON.stringify(await p.evaluate(()=>({T:window.TOTAL,tr:S.map(s=>[s.start+s.hold,s.m])}))));await b.close()})();
