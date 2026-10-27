"""Multi-turn adapter: reuse the existing model, HTTP, safety and failover client."""
import copy
from .gemini_client import Gemini


class AgentPrompt:
    def __init__(self,question,history,alias,assistant_alias='BOT JAT DESIGN'):
        self.question,self.history,self.alias=question[:1200],history[-6:],alias
        self.assistant_alias=assistant_alias


class ConversationGemini(Gemini):
    def generate(self,question):
        if not isinstance(question,AgentPrompt):return super().generate(question)
        self.turn=question
        try:return super().generate(question.question)
        finally:self.turn=None
    def request(self,path,payload=None):
        turn=getattr(self,'turn',None)
        if turn is not None and payload is not None and path.endswith(':generateContent'):
            payload=copy.deepcopy(payload)
            contents=[]
            for q,a in turn.history:
                contents.extend([{'role':'user','parts':[{'text':q[:1200]}]},
                                 {'role':'model','parts':[{'text':a[:2000]}]}])
            text=('Tên gọi của bot: '+turn.assistant_alias+'. Tên gọi đã xác nhận của người đang hỏi: '+turn.alias+'. '
                  'Chỉ dùng tên này để xưng hô; không đoán tài khoản khác. '
                  'Đây chỉ là hội thoại riêng của người này, không phải lịch sử nhóm.\n'+turn.question)
            contents.append({'role':'user','parts':[{'text':text}]})
            payload['contents']=contents
        return super().request(path,payload)
