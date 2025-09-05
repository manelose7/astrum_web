import os
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from uuid import uuid4
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler('app.log', encoding='utf-8')  # Логи в файл
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    logger.error("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# Удаляем старые файловые константы
# HWID_BINDINGS_FILE = "hwid_bindings.json"
# ALL_KEYS_FILE = "keys.txt"

# Удаляем старые файловые функции
# def load_hwid_bindings():
#     if os.path.exists(HWID_BINDINGS_FILE):
#         try:
#             with open(HWID_BINDINGS_FILE, "r", encoding="utf-8") as f:
#                 return json.load(f)
#         except (json.JSONDecodeError, IOError):
#             return {}
#     return {}

# def save_hwid_bindings(bindings):
#     with open(HWID_BINDINGS_FILE, "w", encoding="utf-8") as f:
#         json.dump(bindings, f, ensure_ascii=False, indent=2)

# def load_all_keys():
#     if os.path.exists(ALL_KEYS_FILE):
#         try:
#             with open(ALL_KEYS_FILE, "r", encoding="utf-8") as f:
#                 return [line.strip() for line in f if line.strip()]
#         except IOError as e:
#             print(f"❌ Ошибка чтения keys.txt: {e}")
#             return []
#     print("⚠️ keys.txt не найден, возвращаем пустой список.")
#     return []

@app.get("/")
def root():
    try:
        logger.info("✅ Запрос к корневому эндпоинту (/): Попытка отдать index.html")
        return FileResponse("index.html")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при отдаче index.html: {e}")
        return JSONResponse(content={"error": "Не удалось загрузить страницу"}, status_code=500)

@app.get("/generate-new-key")
async def generate_new_key():
    try:
        new_key = str(uuid4())
        # Вставляем новый ключ в Supabase
        response = supabase.from_("keys").insert({"key_value": new_key}).execute()
        if response.data:
            logger.info(f"✅ Сгенерирован и добавлен новый ключ в Supabase: {new_key}")
            return PlainTextResponse(content=new_key)
        else:
            logger.error(f"❌ Ошибка при вставке ключа в Supabase: {response.error}")
            return JSONResponse(content={"error": "Ошибка генерации ключа"}, status_code=500)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в /generate-new-key: {e}")
        return JSONResponse(content={"error": "Ошибка генерации ключа"}, status_code=500)

@app.get("/list-keys")
async def list_keys_for_rayfield():
    try:
        # Получаем все ключи из базы данных
        response = supabase.table("keys").select("key_value").execute()
        
        if response.data:
            # Формируем список ключей как plain text
            keys = [key['key_value'] for key in response.data if not key.get('user_id')]
            
            logger.info(f"🔑 Список доступных ключей: {keys}")
            
            return PlainTextResponse("\n".join(keys))
        else:
            logger.warning("❌ В базе нет доступных ключей")
            return PlainTextResponse("")
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка ключей: {e}")
        return PlainTextResponse("")

@app.post("/activate")
async def activate(request: Request):
    try:
        # Получаем сырые данные для максимальной прозрачности
        raw_data = await request.body()
        logger.info(f"🔍 RAW данные запроса: {raw_data}")

        data = await request.json()
        key = data.get("key", "").strip()  # Удаляем пробелы
        user_id = data.get("user_id", "").strip()
        
        logger.info(f"🔑 Попытка активации:")
        logger.info(f"   Полные данные запроса: {data}")
        logger.info(f"   Ключ (RAW): '{data.get('key')}'")
        logger.info(f"   Ключ (stripped): '{key}'")
        logger.info(f"   User ID (RAW): '{data.get('user_id')}'")
        logger.info(f"   User ID (stripped): '{user_id}'")

        if not key or not user_id:
            logger.error("❌ Ошибка активации: Key или User ID отсутствуют.")
            return JSONResponse(content={
                "status": "error", 
                "error": "key and user_id required", 
                "details": {
                    "key_provided": bool(key),
                    "user_id_provided": bool(user_id)
                }
            }, status_code=400)
        
        # Проверяем наличие ключа в Supabase
        response = supabase.from_("keys").select("*", count="exact").eq("key_value", key).execute()
        
        logger.info(f"🔍 Результат поиска ключа: {response}")
        logger.info(f"📊 Количество найденных записей: {response.count}")
        
        if not response.data or response.count == 0:
            # Получаем список всех ключей для отладки
            all_keys_response = supabase.from_("keys").select("key_value, user_id").execute()
            all_keys = [
                {"key": item["key_value"], "user_id": item.get("user_id", "Не привязан")} 
                for item in all_keys_response.data or []
            ]
            
            logger.error(f"❌ Ошибка активации: Неверный ключ: '{key}'")
            logger.info(f"📋 Список всех ключей в базе: {all_keys}")
            
            return JSONResponse(content={
                "status": "error", 
                "error": "Invalid key", 
                "details": {
                    "key": key,
                    "keys_in_db": all_keys
                }
            }, status_code=404)

        key_data = response.data[0]
        logger.info(f"🔐 Данные ключа: {key_data}")
        
        # Если ключ уже привязан к User ID
        if key_data["user_id"]:
            if key_data["user_id"] == user_id:
                logger.info(f"✅ Ключ {key} уже активирован с User ID {user_id} (совпадение).")
                return JSONResponse(content={
                    "status": "ok", 
                    "msg": "Key already activated",
                    "details": {
                        "key": key,
                        "user_id": user_id
                    }
                })
            else:
                logger.error(f"❌ Ключ {key} уже привязан к другому User ID: {key_data['user_id']}. Текущий User ID: {user_id}.")
                return JSONResponse(content={
                    "status": "error", 
                    "error": "Key already bound to another User ID",
                    "details": {
                        "key": key,
                        "original_user_id": key_data['user_id'],
                        "current_user_id": user_id
                    }
                }, status_code=403)
        
        # Привязываем ключ к User ID
        update_response = supabase.from_("keys").update({"user_id": user_id}).eq("key_value", key).execute()
        
        logger.info(f"🔄 Результат обновления: {update_response}")
        
        if update_response.data:
            logger.info(f"✅ Ключ {key} успешно активирован и привязан к User ID: {user_id} в Supabase.")
            return JSONResponse(content={
                "status": "ok", 
                "msg": "Key activated successfully",
                "details": {
                    "key": key,
                    "user_id": user_id
                }
            })
        else:
            logger.error(f"❌ Ошибка при привязке ключа к User ID в Supabase: {update_response.error}")
            return JSONResponse(content={
                "status": "error", 
                "error": "Ошибка привязки ключа",
                "details": {
                    "key": key,
                    "user_id": user_id,
                    "supabase_error": str(update_response.error)
                }
            }, status_code=500)

    except Exception as e:
        logger.error(f"❌ Критическая ошибка в /activate: {e}")
        return JSONResponse(content={
            "status": "error", 
            "error": "Внутренняя ошибка сервера",
            "details": str(e)
        }, status_code=500)

@app.get("/keys")
def list_keys_info():
    try:
        # Получаем все ключи
        all_keys_response = supabase.from_("keys").select("key_value").execute()
        all_keys = [item["key_value"] for item in all_keys_response.data] if all_keys_response.data else []

        # Получаем активированные ключи (те, у которых user_id не NULL)
        activated_keys_response = supabase.from_("keys").select("key_value, user_id").not_("user_id", "is", None).execute()
        activated_keys_details = {item["key_value"]: item["user_id"] for item in activated_keys_response.data} if activated_keys_response.data else {}

        logger.info(f"✅ Запрос /keys из Supabase: {len(all_keys)} ключей, {len(activated_keys_details)} привязок.")
        return JSONResponse(content={
            "total_keys_in_db": len(all_keys),
            "activated_keys_count": len(activated_keys_details),
            "activated_keys_details": activated_keys_details
        })
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в /keys: {e}")
        return JSONResponse(content={"error": "Внутренняя ошибка сервера"}, status_code=500)
