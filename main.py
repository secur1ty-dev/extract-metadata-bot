import asyncio
import os
import subprocess
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import ContentType, Message
from aiogram import types
from aiogram import F
import config


# Логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

user_photo_count = {}


bot = Bot(config.TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    logging.info(f"Отримано команду /start від користувача {message.from_user.id}")
    await message.answer("Привет, это бот для проверки картинки на метаданные,\n Загружать только файлом, или же пересылать собщение")

async def meta_from_photo(filename):
    logging.info(f"Читання метаданих з файлу: {filename}")
    infoDict = {}
    exifToolPath = config.exifToolPath

    imgPath = os.path.join("photos", filename)
    logging.debug(f"Шлях до зображення: {imgPath}")

    try:
        process = await asyncio.create_subprocess_exec(
            exifToolPath, imgPath,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()

        if stderr:
            logging.error(f"Помилка при читанні метаданих: {stderr.decode().strip()}")
            return "Помилка при читанні метаданих"

        for tag in stdout.decode().splitlines():
            line = tag.strip().split(':')
            if len(line) == 2:
                infoDict[line[0].strip()] = line[1].strip()

        meta_info = "\n".join([f"{k}: {v}" for k, v in infoDict.items()])
        
        if not meta_info:
            logging.warning(f"Метадані не знайдені для файлу: {filename}")
            return "Метаданные отсутствуют"

        logging.info(f"Метадані успішно отримані для файлу: {filename}")
        return meta_info
    except Exception as e:
        logging.error(f"Помилка під час отримання метаданих: {str(e)}")
        return "Помилка під час отримання метаданих"

# Обробка документів та фотографій
@dp.message(F.content_type.in_([ContentType.DOCUMENT, ContentType.PHOTO]))
async def document_and_photo_handler(message: types.Message):
    user_id = message.from_user.id
    logging.info(f"Отримано файл від користувача {user_id}")

    if user_id not in user_photo_count:
        user_photo_count[user_id] = 0

    if message.document:
        file_name = message.document.file_name
        file_extension = file_name.split('.')[-1].lower()

        logging.info(f"Отримано документ: {file_name}")
        
        if file_extension not in ALLOWED_EXTENSIONS:
            logging.warning(f"Неправильний тип файлу: {file_extension}")
            await message.reply("Неверный тип файла, поддерживаются лишь изображения.")
            return

        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_extension = "jpg"
        logging.info(f"Отримано фотографію від користувача {user_id}")

    user_photo_count[user_id] += 1
    file_path = os.path.join("photos", f"{user_id}_{user_photo_count[user_id]}.{file_extension}")
    
    await message.bot.download(file_id, destination=file_path.replace("\\", "/"))
    logging.info(f"Файл успішно збережено як {file_path.replace('\\', '/')}.")

    meta_info = await meta_from_photo(f"{user_id}_{user_photo_count[user_id]}.{file_extension}")
    await message.reply(meta_info)


async def main():
    logging.info("Запуск бота")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.info("Запуск основної програми")
    asyncio.run(main())
