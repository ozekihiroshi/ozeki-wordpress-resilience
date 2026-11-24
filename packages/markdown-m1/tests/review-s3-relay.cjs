// Orchestrates isolated infrastructure over existing SSH connections; no credentials copied.
const {spawn}=require('node:child_process');const readline=require('node:readline');
const broker=spawn('ssh',['community','python3','/tmp/owr-review-safe-20261124-broker/review-s3-broker.py']);
const runner=spawn('ssh',['dm','sudo','python3','/tmp/owr-review-safe-20261124/review-s3-relay.py']);
let count=0,completed=false;
broker.stderr.pipe(process.stderr);runner.stderr.pipe(process.stderr);
readline.createInterface({input:broker.stdout}).on('line',line=>{const x=JSON.parse(line);if(x.scope)console.log('Fresh scoped S3 broker ready');runner.stdin.write(line+'\n');});
readline.createInterface({input:runner.stdout}).on('line',line=>{const x=JSON.parse(line);if(x.done){completed=true;console.log(JSON.stringify(x));broker.stdin.end();runner.stdin.end();}else{broker.stdin.write(line+'\n');if(++count%25===0)console.log('S3 operations: '+count);}});
broker.on('close',code=>{if(!completed){console.error('Broker stopped before completion: '+code);runner.kill();process.exitCode=1;}});
runner.on('close',code=>{broker.stdin.end();if(!completed||code)process.exitCode=1;});
