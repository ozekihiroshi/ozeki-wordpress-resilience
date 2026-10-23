const fs=require('fs'),vm=require('vm'),assert=require('assert');
async function scenario(states,fail=false){
 let callbacks={},events=[],applies=0,stops=0,starts=0;
 const up={settings:{multipart_params:{}},bind:(name,fn,scope,priority)=>{callbacks[name]=fn;if(name==='FileUploaded')assert.equal(priority,100);},stop:()=>stops++,start:()=>starts++,trigger:(name,file,response)=>{callbacks[name](up,file,response);events.push(JSON.parse(response.response));}};
 const context={window:{owrNative:{parent:'old'}},setTimeout:fn=>fn(),wp:{Uploader:function(){},apiFetch:async q=>{
  if(q.path.endsWith('/state'))return states.shift();
  if(q.path.endsWith('/apply')){applies++;return {};}
  return {parent:'new',attachment:{id:123}};
 }}};context.window.wp=context.wp;context.wp.Uploader.prototype.init=function(){};
 vm.runInNewContext(fs.readFileSync(require('path').join(__dirname,'../assets/native-materials-upload.js'),'utf8'),context);
 context.wp.Uploader.prototype.init.call({uploader:up});
 const returned=callbacks.FileUploaded(up,{}, {response:JSON.stringify({success:true,data:{owr_pending:true,asset:'image-123',operation:'op'}})});
 assert.equal(returned,false);assert.equal(events.length,0);assert.equal(stops,1);
 await new Promise(resolve=>setTimeout(resolve,10));
 assert.equal(events.length,1);assert.equal(events[0].success,!fail);assert.equal(applies,fail?0:1);assert.equal(starts,fail?0:1);
 if(!fail)assert.equal(context.window.owrNative.parent,'new');
}
(async()=>{
 await scenario([...Array(20).fill({state:'running',pending:{operation:'op'}}),{state:'stored',pending:{operation:'op'}}]);
 await scenario([{state:'failed',pending:{operation:'op'}}],true);
 await scenario([{state:'stored',pending:{operation:'other'}}],true);
 console.log('PASS asynchronous media: delayed success, failure, operation mismatch');
})().catch(e=>{console.error(e);process.exit(1)});

