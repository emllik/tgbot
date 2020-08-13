import asyncio, io, ssl, json

#################################################
#  light asynchronous library for telegram bot  #
#################################################

host = 'api.telegram.org'
buffered = io.BufferedReader

class http_session(object): 
    def __init__(self, token):
        self.api = token
        self.connections = set()

    async def create_connection(self):
        contex = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        return await asyncio.open_connection(host, 443, ssl=contex)

    async def recv(self, reader):
        data = await reader.read(4096)
        if not data:  
            raise BrokenPipeError
        header, recv = data.split(b'\r\n\r\n')
        if not header[9:12] == b'200':
            raise ValueError(recv)
        length = int(header.partition(b'Content-Length: ')[2].partition(b'\r\n')[0])
        while len(recv) != length:
            recv += await reader.read(4096)
        return recv

    async def post(self, url, data):
        payload = bytes()
        #encode to form-data
        for key, value in data.items():
            options = 'name="%s"' % key
            x = type(value)
            if x == str or x == int:
                value = str(value).encode()
            elif x == bytes:
                options += '; filename="%s"' % key
            elif x == buffered:
                options += '; filename="%s"' % value.name
                value = value.read()
            elif x == dict or x == list:
                value = json.dumps(value).encode()
            payload += b'--bound\r\nContent-Disposition: form-data; %s\r\n\r\n%s\r\n' % (options.encode(), value)
        payload += b'--bound--\r\n'
        
        header = (f'POST /bot{self.api}/{url} HTTP/1.1\r\n' +
                  f'Host: {host}\r\n' +
                  f'Connection: keep-alive\r\n' +
                  f'Content-Length: {payload.__len__()}\r\n' +
                  f'Content-Type: multipart/form-data; boundary="bound"\r\n\r\n')
        
        if not self.connections:
            connection = await self.create_connection()
            self.connections.add(connection)
        try: 
            reader, writer = self.connections.pop()
            writer.write(header.encode() + payload)
            response = await self.recv(reader)
            #
        except BrokenPipeError:
            return await self.post(url, data)
        
        self.connections.add((reader, writer))
        data = json.loads(response.decode('utf-8'))
        return de_json(data).result
        
        
class bot:        
    def __init__(self, token, offset=0):
        self.offset = offset
        self.session = http_session(token)
        self.handlers = []

    async def update(self, timeout=120, get_offset=True, limit=None, allowed_updates=None):
        url = 'getUpdates'
        data = {'timeout': timeout, 'offset': self.offset}
        if limit:
            data['limit'] = limit
        if allowed_updates:
            data['allowed_updates'] = allowed_updates
        result = await self.session.post(url, data)
        if result and get_offset:
           self.offset = int(result[-1]['update_id']) + 1
        return result            

    async def downloadFile(self,  file_id):
        patch = await self.getFile(file_id)
        header = f'GET /file/bot{self.session.api}/{patch.file_path} HTTP/1.1\r\nHost: {host}\r\n\r\n'
        reader, writer = await self.session.create_connection()
        writer.write(header.encode())
        return await self.session.recv(reader)                 

    def handler(self, content, types=['text', 'data', 'query'], data=[], func=0):
        def fun(function):
            handler = (content, set(types), set(data), func, function)
            self.handlers.insert((0 if data or func else len(self.handlers)), handler)
            return function
        return fun
        
    def filter(self, update):
       for content, types, data, func, function in self.handlers:
          if not content in update:
              continue
          for type in types.intersection(update[content]):
              if data:
                  lines = update[content][type].split()
                  if data.isdisjoint(lines): continue
              msg = update.__getattr__(content)
              if func and not func(msg):
                      continue
              return function(msg)
              
    async def poll(self):
        data = await self.update()
        updates = filter(None, map(self.filter, data))
        asyncio.ensure_future(self.poll())
        for upd in updates: await upd
        
    async def poll2(self):
        while True:
            data = await self.update()
            updates = [upd for upd in map(self.filter, data) if upd]
            if not updates: continue
            asyncio.ensure_future(asyncio.wait(updates))
            
    def polling(self):
        self.loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.poll())
        self.loop.run_forever()
        
    #API methods
        
    async def getMe(self, token):
        method = 'getMe'
        return await self.session.post(method)    
    
    async def getFile(self, file_id):
        url = 'getFile' 
        data = {'file_id': file_id}
        return await self.session.post(url, data)
                        
    async def sendMsg(self, chat_id, text, disable_web_page_preview=None, reply_to_message_id=None, reply_markup=None,
                     parse_mode=None, disable_notification=None, timeout=None):
        method = 'sendMessage'
        data = {'chat_id': str(chat_id), 'text': text}
        if disable_web_page_preview:
            data['disable_web_page_preview'] = disable_web_page_preview
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if parse_mode:
            data['parse_mode'] = parse_mode
        if disable_notification:
            data['disable_notification'] = disable_notification
        if timeout:
            data['connect-timeout'] = timeout
        return await self.session.post(method, data)    
            
    async def getUserProfilePhotos(self, user_id, offset=None, limit=None):
        method = 'getUserProfilePhotos'
        data = {'user_id': user_id}
        if offset:
            data['offset'] = offset
        if limit:
            data['limit'] = limit
        return await self.session.post(method, data)
        
    async def getChat(self, chat_id):
        method = 'getChat'
        data = {'chat_id': chat_id}
        return await self.session.post(method, data)
        
    async def leaveChat(self, chat_id):
        method = 'leaveChat'
        data = {'chat_id': chat_id}
        return await self.session.post(method, data)    
    
    async def getChatAdministrators(self, chat_id):
        method = 'getChatAdministrators'
        data = {'chat_id': chat_id}
        return await self.session.post(method, data)    
       
    async def getChatMembersCount(self, chat_id):
        method = 'getChatMembersCount'
        data = {'chat_id': chat_id}
        return await self.session.post(method, data)    
    
    async def setChatStickerSet(self, chat_id, sticker_set_name):
        method = 'setChatStickerSet'
        data = {'chat_id': chat_id, 'sticker_set_name': sticker_set_name}
        return await self.session.post(method, data)    
    
    async def deleteChatStickerSet(self, chat_id):
        method = 'deleteChatStickerSet'
        data = {'chat_id': chat_id}
        return await self.session.post(method, data)
        
    async def getChatMember(self, chat_id, user_id):
        method = 'getChatMember'
        data = {'chat_id': chat_id, 'user_id': user_id}
        return await self.session.post(method, data)    
       
    async def forwardMsg(self, chat_id, from_chat_id, message_id, disable_notification=None):
        method = 'forwardMessage'
        data = {'chat_id': chat_id, 'from_chat_id': from_chat_id, 'message_id': message_id}
        if disable_notification:
            data['disable_notification'] = disable_notification
        return await self.session.post(method, data)    
    
    async def sendDice(self, chat_id, emoji=None, disable_notification=None, reply_to_message_id=None, reply_markup=None):
        method = 'sendDice'
        data = {'chat_id': chat_id}
        if emoji:
            data['emoji'] = emoji
        if disable_notification:
            data['disable_notification'] = disable_notification
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)    
    
    async def sendPhoto(self, chat_id, photo, caption=None, reply_to_message_id=None, reply_markup=None,
                   parse_mode=None, disable_notification=None):
        method = 'sendPhoto'
        data = {'chat_id': chat_id}
        data['photo'] = photo
        if caption:
            data['caption'] = caption
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if parse_mode:
            data['parse_mode'] = parse_mode
        if disable_notification:
            data['disable_notification'] = disable_notification
        return await self.session.post(method, data)    
    
    async def sendMediaGroup(self, chat_id, media, disable_notification=None, reply_to_message_id=None):
        method = 'sendMediaGroup'
        data = {'chat_id': chat_id, 'media': media}
        if disable_notification:
            data['disable_notification'] = disable_notification
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        return await self.session.post(method, data)
        
    async def sendLocation(self, chat_id, latitude, longitude, live_period=None, reply_to_message_id=None, reply_markup=None,
                      disable_notification=None):
        method = 'sendLocation'
        data = {'chat_id': chat_id, 'latitude': latitude, 'longitude': longitude}
        if live_period:
            data['live_period'] = live_period
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if disable_notification:
            data['disable_notification'] = disable_notification
        return await self.session.post(method, data)
        
    async def editMsgLiveLocation(self, latitude, longitude, chat_id=None, message_id=None,
                                   inline_message_id=None, reply_markup=None):
        method = 'editMessageLiveLocation'
        data = {'latitude': latitude, 'longitude': longitude}
        if chat_id:
            data['chat_id'] = chat_id
        if message_id:
            data['message_id'] = message_id
        if inline_message_id:
            data['inline_message_id'] = inline_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)
        
    async def stopMsgLiveLocation(self, chat_id=None, message_id=None,
                                   inline_message_id=None, reply_markup=None):
        method = 'stopMessageLiveLocation'
        data = {}
        if chat_id:
            data['chat_id'] = chat_id
        if message_id:
            data['message_id'] = message_id
        if inline_message_id:
            data['inline_message_id'] = inline_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)
        
    async def sendVenue(self, chat_id, latitude, longitude, title, address, foursquare_id=None, disable_notification=None,
                   reply_to_message_id=None, reply_markup=None):
        method = 'sendVenue'
        data = {'chat_id': chat_id, 'latitude': latitude, 'longitude': longitude, 'title': title, 'address': address}
        if foursquare_id:
            data['foursquare_id'] = foursquare_id
        if disable_notification:
            data['disable_notification'] = disable_notification
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)
        
    async def sendContact(self, chat_id, phone_number, first_name, last_name=None, disable_notification=None,
                     reply_to_message_id=None, reply_markup=None):
        method = 'sendContact'
        data = {'chat_id': chat_id, 'phone_number': phone_number, 'first_name': first_name}
        if last_name:
            data['last_name'] = last_name
        if disable_notification:
            data['disable_notification'] = disable_notification
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)
        
    async def sendChatAction(self, chat_id, action):
        method = 'sendChatAction'
        data = {'chat_id': chat_id, 'action': action}
        return await self.session.post(method, data)
        
    async def sendVideo(self, chat_id, file, duration=None, caption=None, reply_to_message_id=None, reply_markup=None,
                   parse_mode=None, supports_streaming=None, disable_notification=None, timeout=None):
        method = 'sendVideo'
        data = {'chat_id': chat_id, 'video': file}
        if duration:
            data['duration'] = duration
        if caption:
            data['caption'] = caption
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if parse_mode:
            data['parse_mode'] = parse_mode
        if supports_streaming:
            data['supports_streaming'] = supports_streaming
        if disable_notification:
            data['disable_notification'] = disable_notification
        if timeout:
            data['connect-timeout'] = timeout
        return await self.session.post(method, data)    
    
    async def sendAnimation(self, chat_id, file, duration=None, caption=None, reply_to_message_id=None, reply_markup=None,
                   parse_mode=None, disable_notification=None, timeout=None):
        method = 'sendAnimation'
        data = {'chat_id': chat_id, 'animation': file}
        if duration:
            data['duration'] = duration
        if caption:
            data['caption'] = caption
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if parse_mode:
            data['parse_mode'] = parse_mode
        if disable_notification:
            data['disable_notification'] = disable_notification
        if timeout:
            data['connect-timeout'] = timeout
        return await self.session.post(method, data)    
    
    async def sendVoice(self, chat_id, voice, caption=None, duration=None, reply_to_message_id=None, reply_markup=None,
                   parse_mode=None, disable_notification=None, timeout=None):
        method = 'sendVoice'
        data = {'chat_id': chat_id}
        data['voice'] = voice
        if caption:
            data['caption'] = caption
        if duration:
            data['duration'] = duration
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if parse_mode:
            data['parse_mode'] = parse_mode
        if disable_notification:
            data['disable_notification'] = disable_notification
        if timeout:
            data['connect-timeout'] = timeout
        return await self.session.post(method, data)
        
    async def sendVideoNote(self, chat_id, file, duration=None, length=639, reply_to_message_id=None, reply_markup=None,
                        disable_notification=None, timeout=None):
        method = 'sendVideoNote'
        data = {'chat_id': chat_id, 'video_note': file}
        if duration:
            data['duration'] = duration
        if length:
            data['length'] = length
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if disable_notification:
            data['disable_notification'] = disable_notification
        if timeout:
            data['connect-timeout'] = timeout
        return await self.session.post(method, data)
        
    async def sendAudio(self, chat_id, audio, caption=None, duration=None, performer=None, title=None, reply_to_message_id=None,
                   reply_markup=None, parse_mode=None, disable_notification=None, timeout=None):
        method = 'sendAudio'
        data = {'chat_id': chat_id}
        data['audio'] = audio
        if caption:
            data['caption'] = caption
        if duration:
            data['duration'] = duration
        if performer:
            data['performer'] = performer
        if title:
            data['title'] = title
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if parse_mode:
            data['parse_mode'] = parse_mode
        if disable_notification:
            data['disable_notification'] = disable_notification
        if timeout:
            data['connect-timeout'] = timeout
        return await self.session.post(method, data)
        
    async def sendSticker(self, chat_id, file, reply_to_message_id=None, reply_markup=None, parse_mode=None,
                  disable_notification=None, timeout=None, caption=None):
        method = 'sendSticker'
        data = {'chat_id': chat_id, 'sticker': file}
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if parse_mode and data_type == 'document':
            data['parse_mode'] = parse_mode
        if disable_notification:
            data['disable_notification'] = disable_notification
        if timeout:
            data['connect-timeout'] = timeout
        if caption:
            data['caption'] = caption
        return await self.session.post(method, data)

    async def sendDocument(self, chat_id, file, reply_to_message_id=None, reply_markup=None, parse_mode=None,
                  disable_notification=None, timeout=None, caption=None):
        method = 'sendDocument'
        data = {'chat_id': chat_id, 'document': file}
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if parse_mode and data_type == 'document':
            data['parse_mode'] = parse_mode
        if disable_notification:
            data['disable_notification'] = disable_notification
        if timeout:
            data['connect-timeout'] = timeout
        if caption:
            data['caption'] = caption
        return await self.session.post(method, data)
        
    async def kickChatMember(self, chat_id, user_id, until_date=None):
        method = 'kickChatMember'
        data = {'chat_id': chat_id, 'user_id': user_id}
        if until_date:
            data['until_date'] = until_date
        return await self.session.post(method, data)    
    
    async def unbanChatMember(self, chat_id, user_id):
        method = 'unbanChatMember'
        data = {'chat_id': chat_id, 'user_id': user_id}
        return await self.session.post(method, data)
      
    async def restrictChatMember(self, chat_id, user_id, until_date=None, can_send_messages=None,
                             can_send_media_messages=None, can_send_other_messages=None,
                             can_add_web_page_previews=None, can_invite_users=None):
        method = 'restrictChatMember'
        data = {'chat_id': chat_id, 'user_id': user_id}
        if until_date:
            data['until_date'] = until_date
        if can_send_messages:
            data['can_send_messages'] = can_send_messages
        if can_send_media_messages:
            data['can_send_media_messages'] = can_send_media_messages
        if can_send_other_messages:
            data['can_send_other_messages'] = can_send_other_messages
        if can_add_web_page_previews:
            data['can_add_web_page_previews'] = can_add_web_page_previews
        if can_invite_users:
            data['can_invite_users'] = can_invite_users
        return await self.session.post(method, data)
        
    async def promoteChatMember(self, chat_id, user_id, can_change_info=None, can_post_messages=None,
                            can_edit_messages=None, can_delete_messages=None, can_invite_users=None,
                            can_restrict_members=None, can_pin_messages=None, can_promote_members=None):
        method = 'promoteChatMember'
        data = {'chat_id': chat_id, 'user_id': user_id}
        if can_change_info:
            data['can_change_info'] = can_change_info
        if can_post_messages:
            data['can_post_messages'] = can_post_messages
        if can_edit_messages:
            data['can_edit_messages'] = can_edit_messages
        if can_delete_messages:
            data['can_delete_messages'] = can_delete_messages
        if can_invite_users:
            data['can_invite_users'] = can_invite_users
        if can_restrict_members:
            data['can_restrict_members'] = can_restrict_members
        if can_pin_messages:
            data['can_pin_messages'] = can_pin_messages
        if can_promote_members:
            data['can_promote_members'] = can_promote_members
        return await self.session.post(method, data)
        
    async def setChatAdministratorCustomTitle(self, chat_id, user_id, custom_title):
        method = 'setChatAdministratorCustomTitle'
        data = {
            'chat_id': chat_id, 'user_id': user_id, 'custom_title': custom_title}
        return await self.session.post(method, data)
        
    async def setChatPermissions(self, chat_id, permissions):
        method = 'setChatPermissions'
        data = {
            'chat_id': chat_id,
            'permissions': permissions}
        return await self.session.post(method, data)    
    
    async def exportChatInviteLink(self, chat_id):
        method = 'exportChatInviteLink'
        data = {'chat_id': chat_id}
        return await self.session.post(method, data)    
    
    async def setChatPhoto(self, chat_id, photo):
        method = 'setChatPhoto'
        data = {'chat_id': chat_id}
        data['photo'] = photo
        return await self.session.post(method, data)    
    
    async def deleteChatPhoto(self, chat_id):
        method = 'deleteChatPhoto'
        data = {'chat_id': chat_id}
        return await self.session.post(method, data)
        
    async def setChatTitle(self, chat_id, title):
        method = 'setChatTitle'
        data = {'chat_id': chat_id, 'title': title}
        return await self.session.post(method, data)
        
    async def setMyCommands(self, commands):
        method = 'setMyCommands'
        data = {'commands': commands}
        return await self.session.post(method, data)    
    
    async def setChatDescription(self, chat_id, description):
        method = 'setChatDescription'
        data = {'chat_id': chat_id, 'description': description}
        return await self.session.post(method, data)
        
    async def pinChatMsg(self, chat_id, message_id, disable_notification=False):
        method = 'pinChatMessage'
        data = {'chat_id': chat_id, 'message_id': message_id, 'disable_notification': disable_notification}
        return await self.session.post(method, data)
        
    async def unpinChatMsg(self, chat_id):
        method = 'unpinChatMessage'
        data = {'chat_id': chat_id}
        return await self.session.post(method, data)    
    
    # Updating messages
    
    async def editMsgText(self, text, chat_id=None, message_id=None, inline_message_id=None, parse_mode=None,
                          disable_web_page_preview=None, reply_markup=None):
        method = 'editMessageText'
        data = {'text': text}
        if chat_id:
            data['chat_id'] = chat_id
        if message_id:
            data['message_id'] = message_id
        if inline_message_id:
            data['inline_message_id'] = inline_message_id
        if parse_mode:
            data['parse_mode'] = parse_mode
        if disable_web_page_preview:
            data['disable_web_page_preview'] = disable_web_page_preview
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)
        
    async def editMsgCaption(self, caption, chat_id=None, message_id=None, inline_message_id=None,
                             parse_mode=None, reply_markup=None):
        method = 'editMessageCaption'
        data = {'caption': caption}
        if chat_id:
            data['chat_id'] = chat_id
        if message_id:
            data['message_id'] = message_id
        if inline_message_id:
            data['inline_message_id'] = inline_message_id
        if parse_mode:
            data['parse_mode'] = parse_mode
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)
        
    async def editMsgMedia(self, media, chat_id=None, message_id=None, inline_message_id=None, reply_markup=None):
        method = 'editMessageMedia'
        data = {'media': media}
        if chat_id:
            data['chat_id'] = chat_id
        if message_id:
            data['message_id'] = message_id
        if inline_message_id:
            data['inline_message_id'] = inline_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)
        
    async def editMsgReplyMarkup(self, chat_id=None, message_id=None, inline_message_id=None, reply_markup=None):
        method = 'editMessageReplyMarkup'
        data = {}
        if chat_id:
            data['chat_id'] = chat_id
        if message_id:
            data['message_id'] = message_id
        if inline_message_id:
            data['inline_message_id'] = inline_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)
        
    async def deleteMsg(self, chat_id, message_id):
        method = 'deleteMessage'
        data = {'chat_id': chat_id, 'message_id': message_id}
        return await self.session.post(method, data)    
    
    # Game
    
    async def sendGame(self, chat_id, game_short_name, disable_notification=None, reply_to_message_id=None, reply_markup=None):
        method = 'sendGame'
        data = {'chat_id': chat_id, 'game_short_name': game_short_name}
        if disable_notification:
            data['disable_notification'] = disable_notification
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)
        
    async def setGameScore(self, user_id, score, force=None, disable_edit_message=None, chat_id=None, message_id=None,
                       inline_message_id=None):
        method = 'setGameScore'
        data = {'user_id': user_id, 'score': score}
        if force:
            data['force'] = force
        if chat_id:
            data['chat_id'] = chat_id
        if message_id:
            data['message_id'] = message_id
        if inline_message_id:
            data['inline_message_id'] = inline_message_id
        if disable_edit_message:
            data['disable_edit_message'] = disable_edit_message
        return await self.session.post(method, data)
        
    async def getGameHighScores(self, user_id, chat_id=None, message_id=None, inline_message_id=None):
        method = 'getGameHighScores'
        data = {'user_id': user_id}
        if chat_id:
            data['chat_id'] = chat_id
        if message_id:
            data['message_id'] = message_id
        if inline_message_id:
            data['inline_message_id'] = inline_message_id
        return await self.session.post(method, data)    
    
    # Payments
    
    async def sendInvoice(self, chat_id, title, description, invoice_data, provider_token, currency, prices,
                     start_parameter, photo_url=None, photo_size=None, photo_width=None, photo_height=None,
                     need_name=None, need_phone_number=None, need_email=None, need_shipping_address=None, is_flexible=None,
                     disable_notification=None, reply_to_message_id=None, reply_markup=None, provider_data=None):
    
        method = 'sendInvoice'
        data = {'chat_id': chat_id, 'title': title, 'description': description, 'data': invoice_data,
                   'provider_token': provider_token, 'start_parameter': start_parameter, 'currency': currency,
                   'prices': prices}
        if photo_url:
            data['photo_url'] = photo_url
        if photo_size:
            data['photo_size'] = photo_size
        if photo_width:
            data['photo_width'] = photo_width
        if photo_height:
            data['photo_height'] = photo_height
        if need_name:
            data['need_name'] = need_name
        if need_phone_number:
            data['need_phone_number'] = need_phone_number
        if need_email:
            data['need_email'] = need_email
        if need_shipping_address:
            data['need_shipping_address'] = need_shipping_address
        if is_flexible:
            data['is_flexible'] = is_flexible
        if disable_notification:
            data['disable_notification'] = disable_notification
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        if provider_data:
            data['provider_data'] = provider_data
        return await self.session.post(method, data)
        
    async def answerShippingQuery(self, shipping_query_id, ok, shipping_options=None, error_message=None):
        method = 'answerShippingQuery'
        data = {'shipping_query_id': shipping_query_id, 'ok': ok}
        if shipping_options:
            data['shipping_options'] = shipping_options
        if error_message:
            data['error_message'] = error_message
        return await self.session.post(method, data)
        
    async def answerPreCheckoutQuery(self, pre_checkout_query_id, ok, error_message=None):
        method = 'answerPreCheckoutQuery'
        data = {'pre_checkout_query_id': pre_checkout_query_id, 'ok': ok}
        if error_message:
            data['error_message'] = error_message
        return await self.session.post(method, data)
        
    # InlineQuery
    
    async def answerCallbackQuery(self, callback_query_id, text=None, show_alert=None, url=None, cache_time=None):
        method = 'answerCallbackQuery'
        data = {'callback_query_id': callback_query_id}
        if text:
            data['text'] = text
        if show_alert:
            data['show_alert'] = show_alert
        if url:
            data['url'] = url
        if cache_time:
            data['cache_time'] = cache_time
        return await self.session.post(method, data)    
    
    async def answerInlineQuery(self, inline_query_id, results, cache_time=None, is_personal=None, next_offset=None,
                            switch_pm_text=None, switch_pm_parameter=None):
        method = 'answerInlineQuery'
        data = {'inline_query_id': inline_query_id, 'results': results}
        if cache_time:
            data['cache_time'] = cache_time
        if is_personal:
            data['is_personal'] = is_personal
        if next_offset:
            data['next_offset'] = next_offset
        if switch_pm_text:
            data['switch_pm_text'] = switch_pm_text
        if switch_pm_parameter:
            data['switch_pm_parameter'] = switch_pm_parameter
        return await self.session.post(method, data)
        
    async def getStickerSet(self, name):
        method = 'getStickerSet'
        return await self.session.post(method, data={'name': name})
        
    async def uploadStickerFile(self, user_id, png_sticker):
        method = 'uploadStickerFile'
        data = {'user_id': user_id}
        data = {'png_sticker': png_sticker}
        return await self.session.post(method, data)
        
    async def createNewStickerSet(self, user_id, name, title, png_sticker, emojis, contains_masks=None, mask_position=None):
        method = 'createNewStickerSet'
        data = {'user_id': user_id, 'name': name, 'title': title, 'emojis': emojis}
        data['png_sticker'] = png_sticker
        if contains_masks:
            data['contains_masks'] = contains_masks
        if mask_position:
            data['mask_position'] = mask_position.to_json()
        return await self.session.post(method, data)
        
    async def addStickerToSet(self, user_id, name, png_sticker, emojis, mask_position):
        method = 'addStickerToSet'
        data = {'user_id': user_id, 'name': name, 'emojis': emojis}
        data['png_sticker'] = png_sticker
        if mask_position:
            data['mask_position'] = mask_position.to_json()
        return await self.session.post(method, data)
        
    async def setStickerPositionInSet(self, sticker, position):
        method = 'setStickerPositionInSet'
        data = {'sticker': sticker, 'position': position}
        return await self.session.post(method, data)    
    
    async def deleteStickerFromSet(self, sticker):
        method = 'deleteStickerFromSet'
        data = {'sticker': sticker}
        return await self.session.post(method, data)
        
    async def sendPoll(self, 
            chat_id,
            question, options,
            is_anonymous = None, type = None, allows_multiple_answers = None, correct_option_id = None,
            explanation = None, explanation_parse_mode=None, open_period = None, close_date = None, is_closed = None,
            disable_notifications=False, reply_to_message_id=None, reply_markup=None):
        method = 'sendPoll'
        data = {
            'chat_id': str(chat_id),
            'question': question,
            'options': options}    
        if is_anonymous:
            data['is_anonymous'] = is_anonymous
        if type:
            data['type'] = type
        if allows_multiple_answers:
            data['allows_multiple_answers'] = allows_multiple_answers
        if correct_option_id:
            data['correct_option_id'] = correct_option_id
        if explanation:
            data['explanation'] = explanation
        if explanation_parse_mode:
            data['explanation_parse_mode'] = explanation_parse_mode
        if open_period:
            data['open_period'] = open_period
        if close_date:
            data['close_date'] = close_date
        if is_closed:
            data['is_closed'] = is_closed
    
        if disable_notifications:
            data['disable_notification'] = disable_notifications
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)    
    
    async def stopPoll(self, chat_id, message_id, reply_markup=None):
        method = 'stopPoll'
        data = {'chat_id': str(chat_id), 'message_id': message_id}
        if reply_markup:
            data['reply_markup'] = reply_markup
        return await self.session.post(method, data)

#utils !
               
class de_json(dict):
    def __getattr__(self, name):
        if name == 'sender':
            value = self['from']
        else:
            value = self[name]
        if type(value) == list:
            return [de_json(item) for item in value]
        elif type(value) == dict:
            return de_json(value)   
        return value

       
def keyboard(rows, resize_keyboard=True, one_time_keyboard=False):
     keyboard = {"resize_keyboard": resize_keyboard, "one_time_keyboard": one_time_keyboard, "keyboard": rows}
     return json.dumps(keyboard)
    
def inlineKeyboard(rows):
    inline_keyboard = {"inline_keyboard": rows }
    return json.dumps(inline_keyboard)