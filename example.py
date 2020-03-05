import tgbot

bot = tgbot.bot('token')


@bot.handler('message', types=['text'], data=['/start'])
def welcome(msg):
    bot.sendMsg(msg.chat.id, 'Welcome')


@bot.handler('message', types=['text'])
def text(msg):
    msg.text = msg.text.lower()

    if msg.text in ['hi', 'hello', 'привет', 'ку']:
        bot.sendMsg(msg.chat.id, f'Привет {msg.sender.first_name}')     
        
    elif msg.text == '/help':
        bot.sendMsg(msg.chat.id, '?', tgbot.keyboard([["/help", "/test"], ['audio', 'photo']]))                

    elif msg.text == '/test':
        keyboard = [[{'text': 'Да', 'callback_data': 'yes'}, {'text': 'Нет', 'callback_data': 'no'}]]
        bot.sendMsg(msg.chat.id, 'Test', tgbot.inlineKeyboard(keyboard))   

    elif msg.text == 'photo':
        #file = open('file.jpg', 'rb')
        file = 'AgADAgADfasxG9M74EvoTaxPhhcjLuXLuQ8ABAEAAwIAA20AAy3nBgABFgQ'
        bot.sendPhoto(msg.chat.id, file)      
 
    elif msg.text == 'audio':
        bot.sendAudio(msg.chat.id, 'https://uzimusic.ru/mp3/3419665/Uicideboy_-_Kill_Yourself(uzimusic.ru).mp3')
    

@bot.handler('message', types=['photo'])
def photo(msg):
    file = file_id = msg.photo[-1]['file_id']
    #file = bot.downloadFile(file_id)
    bot.sendPhoto(msg.chat.id, file)
    

@bot.handler('callback_query', types=['data'])
def callback(call):
    msg = call.message

    if call.data == 'yes':
        bot.answerCallbackQuery(call.id, 'Ты нажал да')
    elif call.data == 'no':
        bot.answerCallbackQuery(call.id, 'Ты нажал нет')
            

bot.polling()