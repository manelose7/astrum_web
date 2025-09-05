import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from uuid import uuid4
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import json

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
        print("✅ Запрос к корневому эндпоинту (/): Попытка отдать index.html")
        return FileResponse("index.html")
    except Exception as e:
        print(f"❌ Критическая ошибка при отдаче index.html: {e}")
        return JSONResponse(content={"error": "Не удалось загрузить страницу"}, status_code=500)

@app.get("/generate-new-key")
async def generate_new_key():
    try:
        new_key = str(uuid4())
        # Вставляем новый ключ в Supabase
        response = supabase.from_("keys").insert({"key_value": new_key}).execute()
        if response.data:
            print(f"✅ Сгенерирован и добавлен новый ключ в Supabase: {new_key}")
            return PlainTextResponse(content=new_key)
        else:
            print(f"❌ Ошибка при вставке ключа в Supabase: {response.error}")
            return JSONResponse(content={"error": "Ошибка генерации ключа"}, status_code=500)
    except Exception as e:
        print(f"❌ Критическая ошибка в /generate-new-key: {e}")
        return JSONResponse(content={"error": "Ошибка генерации ключа"}, status_code=500)

@app.get("/list-keys")
async def list_keys_for_rayfield():
    try:
        # Запрашиваем все ключи из Supabase
        response = supabase.from_("keys").select("key_value").execute()
        if response.data:
            all_keys = [item["key_value"] for item in response.data]
            print(f"✅ Отправлен список ключей для Rayfield из Supabase. Количество: {len(all_keys)}")
            return PlainTextResponse(content="\n".join(all_keys))
        else:
            print(f"❌ Ошибка при получении списка ключей из Supabase: {response.error}")
            return JSONResponse(content={"error": "Ошибка получения списка ключей"}, status_code=500)
    except Exception as e:
        print(f"❌ Ошибка при отправке списка ключей Rayfield: {e}")
        return JSONResponse(content={"error": "Ошибка получения списка ключей"}, status_code=500)

@app.post("/activate")
async def activate(request: Request):
    try:
        data = await request.json()
        key = data.get("key")
        hwid = data.get("hwid")
        
        print(f"🔑 Попытка активации: Key={key}, HWID={hwid}")

        if not key or not hwid:
            print("❌ Ошибка активации: Key или HWID отсутствуют.")
            return JSONResponse(content={"error": "key and hwid required"}, status_code=400)
        
        # Проверяем наличие ключа в Supabase
        response = supabase.from_("keys").select("*", count="exact").eq("key_value", key).execute()
        if not response.data or response.count == 0:
            print(f"❌ Ошибка активации: Неверный ключ: {key}")
            return JSONResponse(content={"error": "Invalid key"}, status_code=404)

        key_data = response.data[0]
        
        # Если ключ уже привязан к HWID
        if key_data["hwid"]:
            if key_data["hwid"] == hwid:
                print(f"✅ Ключ {key} уже активирован с HWID {hwid} (совпадение).")
                return JSONResponse(content={"status": "ok", "msg": "Key already activated"})
            else:
                print(f"❌ Ключ {key} уже привязан к другому HWID: {key_data['hwid']}. Текущий HWID: {hwid}.")
                return JSONResponse(content={"error": "Key already bound to another HWID"}, status_code=403)
        
        # Привязываем ключ к HWID
        update_response = supabase.from_("keys").update({"hwid": hwid}).eq("key_value", key).execute()
        if update_response.data:
            print(f"✅ Ключ {key} успешно активирован и привязан к HWID: {hwid} в Supabase.")
            return JSONResponse(content={"status": "ok", "msg": "Key activated successfully"})
        else:
            print(f"❌ Ошибка при привязке ключа к HWID в Supabase: {update_response.error}")
            return JSONResponse(content={"error": "Ошибка привязки ключа"}, status_code=500)

    except Exception as e:
        print(f"❌ Критическая ошибка в /activate: {e}")
        return JSONResponse(content={"error": "Внутренняя ошибка сервера"}, status_code=500)

@app.get("/keys")
def list_keys_info():
    try:
        # Получаем все ключи
        all_keys_response = supabase.from_("keys").select("key_value").execute()
        all_keys = [item["key_value"] for item in all_keys_response.data] if all_keys_response.data else []

        # Получаем активированные ключи (те, у которых hwid не NULL)
        activated_keys_response = supabase.from_("keys").select("key_value, hwid").not_("hwid", "is", None).execute()
        activated_keys_details = {item["key_value"]: item["hwid"] for item in activated_keys_response.data} if activated_keys_response.data else {}

        print(f"✅ Запрос /keys из Supabase: {len(all_keys)} ключей, {len(activated_keys_details)} привязок.")
        return JSONResponse(content={
            "total_keys_in_db": len(all_keys),
            "activated_keys_count": len(activated_keys_details),
            "activated_keys_details": activated_keys_details
        })
    except Exception as e:
        print(f"❌ Критическая ошибка в /keys: {e}")
        return JSONResponse(content={"error": "Внутренняя ошибка сервера"}, status_code=500)
