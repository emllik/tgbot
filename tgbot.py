import socket, ssl, json

####################################
#  light library for telegram bot  #
####################################

host = 'api.telegram.org'
from io import BufferedReader as buffered

class http_session(object): 
    def __init__(self, token, proxy):
        self.api = token
        self.proxy = proxy
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if proxy:
            sock.connect(proxy)
        else:
            contex = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            sock = contex.wrap_socket(sock, server_hostname=host)
            sock.connect((host, 443))
        self.sock = sock
    
    def recv(self):
        data = self.sock.recv(4096)
        if data == b'':  
            raise BrokenPipeError
        header, recv = data.split(b'\r\n\r\n')
        if header[9:12] != b'200':
            raise ValueError(recv)
        leght = int(header.split(b'Content-Length: ')[1].split(b'\r\n')[0])
        while len(recv) != length:
            recv += sock.recv(4096)
        return recv

    def post(self, url, data):
        request = b''
        for key, value in data.items():
            options = 'name="%s"' % key
            if type(value) == str: 
                value = value.encode()
            elif type(value) == bytes:
                options += '; filename="%s"' % key
            elif type(value) == buffered:
                options += '; filename="%s"' % value.name
                value = value.read()
            request += b'--bound\r\nContent-Disposition: form-data; %s\r\n\r\n%s\r\n' % (options.encode(), value)
        request += (b'--bound--\r\n')
        
        header = 'POST /bot{0}/{1} HTTP/1.1\r\nHost: {2}\r\nConnection: keep-alive\r\nContent-Length: {3}\r\nContent-Type: multipart/form-data; boundary="bound"\r\n\r\n'.format(self.api, url, host, len(request))
        try: 
            self.sock.send(header.encode()+request)
            response = self.recv()
        except BrokenPipeError:
            self.__init__(self.api, self.proxy)
            return self.post(url, data)
        return json.loads(response.decode())['result']


class bot(object):
    def __init__(self, token, offset=0, proxy=None):
        self.offset = offset
        self.session = http_session(token, proxy)
        self.handlers = []
        
    def deleteMsg(self, chat_id, msg_id):
         url = 'deleteMessage'
         data = { 'chat_id': str(chat_id), 'message_id': str(msg_id) }
         return self.session.post(url, data)
         
    def update(self, timeout=300, get_offset=True):
        url = 'getUpdates'
        result = self.session.post(url, { 'timeout': str(timeout), 'offset': str(self.offset) })
        if result and get_offset:
           self.offset = int(result[-1]['update_id']) + 1
        return result

    def sendMsg(self, chat_id, text, reply_markup=None, parse_mode=None, reply_to_msg_id=None):
         url = 'sendMessage'
         data = { 'chat_id': str(chat_id), 'text': str(text)}
         if reply_markup:
             data['reply_markup'] = reply_markup
         if parse_mode:
             data['parse_mode'] = parse_mode
         if reply_to_msg_id:
             data['reply_to_message_id'] = reply_to_msg_id
         return self.session.post(url, data)        
                        
    def sendPhoto(self, chat_id, file, caption='', reply_markup=None, reply_to_msg_id=None, parse_mode=None):
        url = 'sendPhoto'
        data = { 'chat_id': str(chat_id), 'photo': file, 'caption': str(caption)}
        if reply_markup:
            data['reply_markup'] = reply_markup
        if reply_to_msg_id:
            data['reply_to_message_id'] = reply_to_msg_id
        if parse_mode:
            data['parse_mode'] = parse_mode
        return self.session.post(url, data)
        
    def sendAudio(self, chat_id, file, caption='', reply_markup=None, reply_to_msg_id=None, parse_mode=None):
        url = 'sendAudio'
        data = { 'chat_id': str(chat_id), 'audio': file, 'caption': str(caption)}
        if reply_markup:
             data['reply_markup'] = reply_markup
        if reply_to_msg_id:
             data['reply_to_message_id'] = reply_to_msg_id
        if parse_mode:
             data['parse_mode'] = parse_mode
        return self.session.post(url, data)
    
    def sendVideo(self, chat_id, file, caption='', reply_markup=None, reply_to_msg_id=None, parse_mode=None):
        url = 'sendVideo'
        data = { 'chat_id': str(chat_id), 'video': file, 'caption': str(caption)}
        if reply_markup:
             data['reply_markup'] = reply_markup
        if reply_to_msg_id:
             data['reply_to_message_id'] = reply_to_msg_id
        if parse_mode:
             data['parse_mode'] = parse_mode
        return self.session.post(url, data)
        
    def sendFile(self, chat_id, file, caption='', reply_markup=None, reply_to_msg_id=None, parse_mode=None):
        url = 'sendDocument'
        data = { 'chat_id': str(chat_id), 'document': file, 'caption': str(caption)}
        if reply_markup:
             data['reply_markup'] = reply_markup
        if reply_to_msg_id:
             data['reply_to_message_id'] = reply_to_msg_id
        if parse_mode:
             data['parse_mode'] = parse_mode
        return self.session.post(url, data)
    
    def getFile(self, file_id):
        url = 'getFile' 
        data = { 'file_id': str(file_id) }
        return self.session.post(url, data)
        
    def downloadFile(self,  file_id):
        patch = self.getFile(file_id)['file_path']
        header = 'GET /file/bot{0}/{1} HTTP/1.1\r\nHost: {2}\r\n\r\n'.format(self.session.api, patch, host)
        self.session.sock.send(header.encode())
        return self.session.recv()

    def editMsgText(self, chat_id, msg_id, text, reply_markup=None, parse_mode=None):
         url = 'editMessageText'
         data = { 'chat_id': str(chat_id), 'message_id': str(msg_id), 'text': str(text) }
         if reply_markup:
             data['reply_markup'] = reply_markup
         if parse_mode:
             data['parse_mode'] = parse_mode
         return self.session.post(url, data)
                        
    def editMsgReplyMarkup(self, chat_id, msg_id, reply_markup):
        url = 'editMessageReplyMarkup'
        data = { 'chat_id': str(chat_id), 'message_id': str(msg_id), 'reply_markup': reply_markup }
        return self.session.post(url, data)
        
    def editMsgCaption(self, chat_id, msg_id, caption, reply_markup=None, parse_mode=None):
        url = 'editMessageCaption'
        data = { 'chat_id': str(chat_id), 'message_id': str(msg_id), 'caption': str(caption) }
        if reply_markup:
             data['reply_markup'] = reply_markup
        if parse_mode:
             data['parse_mode'] = parse_mode
        return self.session.post(url, data)
        
    def forwardMsg(chat_id, from_chat_id, msg_id):
        url = 'forwardMessage'
        data = { 'chat_id': str(chat_id), 'from_chat_id': from_chat_id, 'message_id': str(msg_id) }
        return self.session.post(url, data)
        
    def answerCallbackQuery(self, id, text=None, url=None):
        urll = 'answerCallbackQuery'
        data = { 'callback_query_id': str(id) }
        if url: data['url'] = url
        if text: data['text'] = str(text)
        return self.session.post(urll, data)

    def answerInlineQuery(self, id, results, cache_time=None, is_personal=None, next_offset=None, switch_pm_text=None):
        url = 'answerInlineQuery'
        data = {'inline_query_id': str(id), 'results': results}
        if cache_time:
            data['cache_time'] = str(cache_time)
        if is_personal:
            data['is_personal'] = is_personal
        if next_offset:
            data['next_offset'] = str(next_offset)
        if switch_pm_text:
            data['switch_pm_text'] = switch_pm_text
    
    def handler(self, content, types, data=[]):
        def fun(function):
            handler = (content, set(types), data, function)
            if data:
                self.handlers.insert(0, handler)
            else:
                self.handlers.append(handler)
            return function
        return fun
        
    def filter(self, result): # 
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
                  function(msg)
              if msg: break
                    
    def polling(self, once=False):
        while True:
            data = self.update()
            self.filter(data)
            if once == True: break

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
