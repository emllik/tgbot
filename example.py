import tgbot

bot = tgbot.bot('1061337581:AAH-tgUxpieXarzzJDK8njs-PT_Cau3h-XM')


@bot.handler('message', types=['text'], data=['/start'])
async def welcome(msg):
    await bot.sendMsg(msg.chat.id, 'Welcome')


@bot.handler('message', types=['text'])
async def text(msg):
    msg.text = msg.text.lower()

    if msg.text in ['hi', 'hello', 'привет', 'ку']:
        await bot.sendMsg(msg.chat.id, f'Привет {msg.sender.first_name}')     
        
    elif msg.text == '/help':
        keyboard = tgbot.keyboard([["/help", "/test"], ['audio', 'photo']]
        await bot.sendMsg(msg.chat.id, '?', keyboard))                

    elif msg.text == '/test':
        keyboard = [[{'text': 'Да', 'callback_data': 'yes'}, {'text': 'Нет', 'callback_data': 'no'}]]
        await bot.sendMsg(msg.chat.id, 'Test', tgbot.inlineKeyboard(keyboard))   

    elif msg.text == 'photo':
        #file = open('file.jpg', 'rb')
        file = 'AgADAgADfasxG9M74EvoTaxPhhcjLuXLuQ8ABAEAAwIAA20AAy3nBgABFgQ'
        await bot.sendPhoto(msg.chat.id, file)      
 
    elif msg.text == 'audio':
        await bot.sendAudio(msg.chat.id, 'https://uzimusic.ru/mp3/3419665/Uicideboy_-_Kill_Yourself(uzimusic.ru).mp3')
    

@bot.handler('message', types=['photo'])
async def photo(msg):
    file = file_id = msg.photo[-1]['file_id']
    #file = bot.downloadFile(file_id)
    await bot.sendPhoto(msg.chat.id, file)
    

@bot.handler('callback_query', types=['data'])
async def callback(call):
    msg = call.message

    if call.data == 'yes':
        await bot.answerCallbackQuery(call.id, 'Ты нажал да')
    elif call.data == 'no':
        await bot.answerCallbackQuery(call.id, 'Ты нажал нет')
            

bot.polling()