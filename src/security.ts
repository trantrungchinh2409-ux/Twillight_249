export async function authenticated(actual: string | null, expected?: string): Promise<boolean> {
  if (!expected || expected.length < 8 || expected.length > 256 || !actual || actual.length > 256) return false;
  const digest = (s: string) => crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  const [a,b] = await Promise.all([digest(actual),digest(expected)]);
  const x=new Uint8Array(a), y=new Uint8Array(b);
  let diff=0; for(let i=0;i<x.length;i++) diff |= x[i] ^ y[i];
  return diff===0;
}
export async function boundedJSON(request: Request): Promise<unknown> {
  const reader=request.body?.getReader(); if(!reader) throw new Error('json');
  let size=0; const chunks: Uint8Array[]=[];
  try { while(true) { const {done,value}=await reader.read(); if(done) break;
    size+=value.length; if(size>65536) {await reader.cancel(); throw new Error('large');} chunks.push(value);
  }} finally {reader.releaseLock();}
  const joined=new Uint8Array(size); let at=0; for(const c of chunks){joined.set(c,at);at+=c.length;}
  return JSON.parse(new TextDecoder('utf-8',{fatal:true,ignoreBOM:false}).decode(joined));
}
