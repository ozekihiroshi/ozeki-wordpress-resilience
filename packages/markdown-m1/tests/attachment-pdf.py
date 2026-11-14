"""Nonconfidential one-page fixture; actual WordPress PDF preview generation is tested."""
from pathlib import Path
stream=b'BT /F1 24 Tf 72 700 Td (Attachment recovery fixture) Tj ET'
objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
data=b'%PDF-1.4\n';offsets=[0]
for i,obj in enumerate(objects,1):
 offsets.append(len(data));data+=str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
start=len(data);data+=b'xref\n0 6\n0000000000 65535 f \n'
for x in offsets[1:]:data+=f'{x:010d} 00000 n \n'.encode()
data+=b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(start).encode()+b'\n%%EOF\n'
Path(__file__).with_name('manual.pdf').write_bytes(data)
