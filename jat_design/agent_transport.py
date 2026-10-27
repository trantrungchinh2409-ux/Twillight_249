"""Agent-only official typing API; inherited getUpdates/sendMessage stay unchanged."""
import json
import urllib.error
import urllib.parse
import urllib.request
from .official_api import Transport,OfficialAPI,BASE_URL


class AgentTransport(Transport):
    def typing(self,group):
        if not isinstance(group,str) or not group.strip():return False
        request=urllib.request.Request(BASE_URL+'/bot'+urllib.parse.quote(self._token,safe='')+'/sendChatAction',
            data=json.dumps({'chat_id':group,'action':'typing'}).encode(),
            headers={'Content-Type':'application/json','User-Agent':'JAT-Design/Agent'},method='POST')
        try:
            with self._opener.open(request,timeout=2) as response:
                raw=response.read(65537)
            if len(raw)>65536:return False
            data=json.loads(raw.decode('utf-8'))
            return isinstance(data,dict) and data.get('ok') is True
        except urllib.error.HTTPError as error:
            try:error.close()
            except Exception:pass
            return False
        except Exception:
            return False  # No retry, no raw URL/body/token log, never a chat placeholder.


class AgentAPI(OfficialAPI):
    def typing(self,group):
        self.last_typing_result=self.transport.typing(group)
        return self.last_typing_result
