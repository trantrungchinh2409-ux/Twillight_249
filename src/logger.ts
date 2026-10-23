export function log(requestId: string, result: string) {
  // Both arguments originate in this program, never in request headers/payload.
  console.log(JSON.stringify({request_id:requestId,result}));
}
