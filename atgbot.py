import asyncio, ssl, json

#################################################
#  light asynchronous library for telegram bot  #
#################################################

host = 'api.telegram.org'
from io import BufferedReader as buffered

class http_session(object): 
    def __init__(self, token):
        self.api = token
        self.connections = set()

    async def create_connection(self):
        contex = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        reader, writer = await asyncio.open_connection(host, 443, ssl=contex)
        return (reader, writer)

    async def recv(self, reader):
        data = await reader.read(4096)
        if data == b'':  
            raise BrokenPipeError
        header, recv = data.split(b'\r\n\r\n')
        if header[9:12] != b'200':
            raise ValueError(recv)
        length = int(header.partition(b'Content-Length: ')[2].partition(b'\r\n')[0])
        while len(recv) != length:
            recv += await reader.read(4096)
        return recv

    async def post(self, url, data):
        request = b''
        for key, value in data.items():
            options = 'name="%s"' % key
            if type(value) == str: 
                value = value.encode()
            elif type(value) == int:
                value = str(value).encode()
            elif type(value) == bytes:
                options += '; filename="%s"' % key
            elif type(value) == buffered:
                options += '; filename="%s"' % value.name
                value = value.read()
            request += b'--bound\r\nContent-Disposition: form-data; %s\r\n\r\n%s\r\n' % (options.encode(), value)
        request += (b'--bound--\r\n')
        
        header = 'POST /bot{0}/{1} HTTP/1.1\r\nHost: {2}\r\nConnection: keep-alive\r\nContent-Length: {3}\r\nContent-Type: multipart/form-data; boundary="bound"\r\n\r\n'.format(self.api, url, host, len(request))
        
        if not self.connections:
            connection = await self.create_connection()
            self.connections.add(connection)
        try: 
            reader, writer = self.connections.pop()
            writer.write(header.encode()+request)
            response = await self.recv(reader)
            #...
        except BrokenPipeError:
            return await self.post(url, data)
        
        self.connections.add((reader, writer))
        return json.loads(response.decode('utf-8'))['result']


class bot(object):
    def __init__(self, token, offset=0):
        self.offset = offset
        self.session = http_session(token)
        self.handlers = []
        
    async def deleteMsg(self, chat_id, msg_id):
         url = 'deleteMessage'
         data = { 'chat_id': chat_id, 'message_id': msg_id }
         return await self.session.post(url, data)
         
    async def update(self, timeout=300, get_offset=True):
        url = 'getUpdates'
        data = { 'timeout': timeout, 'offset': self.offset }
        result = await self.session.post(url, data)
        if result and get_offset:
           self.offset = int(result[-1]['update_id']) + 1
        return result

    async def sendMsg(self, chat_id, text, reply_markup=None, parse_mode=None, reply_to_msg_id=None):
         url = 'sendMessage'
         data = { 'chat_id': chat_id, 'text': str(text)}
         if reply_markup:
             data['reply_markup'] = reply_markup
         if parse_mode:
             data['parse_mode'] = parse_mode
         if reply_to_msg_id:
             data['reply_to_message_id'] = reply_to_msg_id
         return await self.session.post(url, data)        
                        
    async def sendPhoto(self, chat_id, file, caption='', reply_markup=None, reply_to_msg_id=None, parse_mode=None):
        url = 'sendPhoto'
        data = { 'chat_id': chat_id, 'photo': file, 'caption': str(caption)}
        if reply_markup:
            data['reply_markup'] = reply_markup
        if reply_to_msg_id:
            data['reply_to_message_id'] = reply_to_msg_id
        if parse_mode:
            data['parse_mode'] = parse_mode
        return await self.session.post(url, data)
        
    async def sendAudio(self, chat_id, file, caption='', reply_markup=None, reply_to_msg_id=None, parse_mode=None):
        url = 'sendAudio'
        data = { 'chat_id': chat_id, 'audio': file, 'caption': str(caption)}
        if reply_markup:
             data['reply_markup'] = reply_markup
        if reply_to_msg_id:
             data['reply_to_message_id'] = reply_to_msg_id
        if parse_mode:
             data['parse_mode'] = parse_mode
        return await self.session.post(url, data)
    
    async def sendVideo(self, chat_id, file, caption='', reply_markup=None, reply_to_msg_id=None, parse_mode=None):
        url = 'sendVideo'
        data = { 'chat_id': chat_id, 'video': file, 'caption': str(caption)}
        if reply_markup:
             data['reply_markup'] = reply_markup
        if reply_to_msg_id:
             data['reply_to_message_id'] = reply_to_msg_id
        if parse_mode:
             data['parse_mode'] = parse_mode
        return await self.session.post(url, data)
        
    async def sendFile(self, chat_id, file, caption='', reply_markup=None, reply_to_msg_id=None, parse_mode=None):
        url = 'sendDocument'
        data = { 'chat_id': chat_id, 'document': file, 'caption': str(caption)}
        if reply_markup:
             data['reply_markup'] = reply_markup
        if reply_to_msg_id:
             data['reply_to_message_id'] = reply_to_msg_id
        if parse_mode:
             data['parse_mode'] = parse_mode
        return await self.session.post(url, data)
    
    async def getFile(self, file_id):
        url = 'getFile' 
        data = { 'file_id': file_id }
        return await self.session.post(url, data)
        
    async def downloadFile(self,  file_id):
        patch = await self.getFile(file_id)['file_path']
        header = 'GET /file/bot{0}/{1} HTTP/1.1\r\nHost: {2}\r\n\r\n'.format(self.session.api, patch, host)
        writer, reader = await self.session.create_session()
        writer.write(header.encode())
        return await self.session.recv(reader)

    async def editMsgText(self, chat_id, msg_id, text, reply_markup=None, parse_mode=None):
         url = 'editMessageText'
         data = { 'chat_id': chat_id, 'message_id': msg_id, 'text': str(text) }
         if reply_markup:
             data['reply_markup'] = reply_markup
         if parse_mode:
             data['parse_mode'] = parse_mode
         return await self.session.post(url, data)
                        
    async def editMsgReplyMarkup(self, chat_id, msg_id, reply_markup):
        url = 'editMessageReplyMarkup'
        data = { 'chat_id': chat_id, 'message_id': msg_id, 'reply_markup': reply_markup }
        return await self.session.post(url, data)
        
    async def editMsgCaption(self, chat_id, msg_id, caption, reply_markup=None, parse_mode=None):
        url = 'editMessageCaption'
        data = { 'chat_id': chat_id, 'message_id': msg_id, 'caption': str(caption) }
        if reply_markup:
             data['reply_markup'] = reply_markup
        if parse_mode:
             data['parse_mode'] = parse_mode
        return await self.session.post(url, data)
        
    async def forwardMsg(chat_id, from_chat_id, msg_id):
        url = 'forwardMessage'
        data = { 'chat_id': chat_id, 'from_chat_id': from_chat_id, 'message_id': msg_id }
        return await self.session.post(url, data)
        
    async def answerCallbackQuery(self, id, text=None, url=None):
        urll = 'answerCallbackQuery'
        data = { 'callback_query_id': id }
        if url: data['url'] = str(url)
        if text: data['text'] = str(text)
        return await self.session.post(urll, data)

    async def answerInlineQuery(self, id, results, cache_time=None, is_personal=None, next_offset=None, switch_pm_text=None):
        url = 'answerInlineQuery'
        data = {'inline_query_id': id, 'results': json.dumps(results) if type(results) == list else results}
        if cache_time:
            data['cache_time'] = cache_time
        if is_personal:
            data['is_personal'] = str(is_personal)
        if next_offset:
            data['next_offset'] = next_offset
        if switch_pm_text:
            data['switch_pm_text'] = str(switch_pm_text)
        return await self.session.post(url, data)
    
    def handler(self, content, types, data=[]):
        def fun(function):
            handler = (content, set(types), data, function)
            if data:
                self.handlers.insert(0, handler)
            else:
                self.handlers.append(handler)
            return function
        return fun
        
    async def filter(self, result): # 
        for update in result:
           msg = None
           for content, types, data, function in self.handlers:
              if not content in update:
                  continue
              for type in types.intersection(update[content]):
                  if data:
                      word = update[content][type].partition(' ')[0]
                      if not word in data: continue
                  msg = dejson(update[content])
                  await function(msg)
              if msg: break
                    
    async def apolling(self):
        while True:
            data = await self.update()
            asyncio.ensure_future(self.filter(data))

    def polling(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.apolling())

##### advance #####

class dejson(dict):
    def __init__(self, data):
        if 'from' in data:
            data['sender'] = data['from']
        self.update(data)
            
    def __getattr__(self, name):
        try: value = self[name]
        except: return None
        if type(value) == dict:
             return dejson(value)
        return value
        
                              
def keyboard(rows, resize_keyboard=True, one_time_keyboard=False):
         keyboard = {"resize_keyboard": resize_keyboard, "one_time_keyboard": one_time_keyboard, "keyboard": rows}
         return json.dumps(keyboard)
    
def inlineKeyboard(rows):
    inline_keyboard = {"inline_keyboard": rows }
    return json.dumps(inline_keyboard)
