"""Loopback-only TCP relay to one dedicated private WordPress address; no cloud access."""
import argparse,asyncio,ipaddress
async def main(address,port):
 async def client(reader,writer):
  upstream=None
  try:
   remote,upstream=await asyncio.wait_for(asyncio.open_connection(address,80),10)
   async def copy(source,target):
    while data:=await asyncio.wait_for(source.read(65536),120):
     target.write(data);await target.drain()
   tasks=[asyncio.create_task(copy(reader,upstream)),asyncio.create_task(copy(remote,writer))]
   done,pending=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
   for task in pending:task.cancel()
   await asyncio.gather(*tasks,return_exceptions=True)
  except (OSError,TimeoutError):pass
  finally:
   writer.close()
   if upstream:upstream.close()
 server=await asyncio.start_server(client,'127.0.0.1',port)
 async with server:await server.serve_forever()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--upstream',required=True);p.add_argument('--port',type=int,required=True);a=p.parse_args()
 ip=ipaddress.ip_address(a.upstream)
 if ip.version!=4 or not ip.is_private or ip.is_loopback or not 1024<=a.port<=65535:p.error('Dedicated private IPv4 and unprivileged port required')
 asyncio.run(main(str(ip),a.port))
