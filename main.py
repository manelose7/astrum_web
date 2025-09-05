from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from uuid import uuid4
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://astrum-web.vercel.app", "https://astrum-web.vercel.app/", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HWID_BINDINGS_FILE = "hwid_bindings.json"
ALL_KEYS_FILE = "keys.txt"

def load_hwid_bindings():
    if os.path.exists(HWID_BINDINGS_FILE):
        try:
            with open(HWID_BINDINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_hwid_bindings(bindings):
    with open(HWID_BINDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(bindings, f, ensure_ascii=False, indent=2)

def load_all_keys():
    if os.path.exists(ALL_KEYS_FILE):
        try:
            with open(ALL_KEYS_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except IOError as e:
            print(f"❌ Ошибка чтения keys.txt: {e}")
            return []
    print("⚠️ keys.txt не найден, возвращаем пустой список.")
    return []

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
        with open(ALL_KEYS_FILE, "a", encoding="utf-8") as f:
            f.write(new_key + "\n")
        print(f"✅ Сгенерирован и добавлен новый ключ: {new_key}")
        return PlainTextResponse(content=new_key)
    except Exception as e:
        print(f"❌ Ошибка генерации нового ключа: {e}")
        return JSONResponse(content={"error": "Ошибка генерации ключа"}, status_code=500)

@app.get("/list-keys")
async def list_keys_for_rayfield():
    try:
        all_keys = load_all_keys()
        print(f"✅ Отправлен список ключей для Rayfield. Количество: {len(all_keys)}")
        return PlainTextResponse(content="\n".join(all_keys))
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
        
        all_valid_keys = load_all_keys()
        if key not in all_valid_keys:
            print(f"❌ Ошибка активации: Неверный ключ: {key}")
            return JSONResponse(content={"error": "Invalid key"}, status_code=404)

        hwid_bindings = load_hwid_bindings()
        
        # Если ключ уже привязан к HWID
        if key in hwid_bindings:
            if hwid_bindings[key] == hwid:
                print(f"✅ Ключ {key} уже активирован с HWID {hwid} (совпадение).")
                return JSONResponse(content={"status": "ok", "msg": "Key already activated"})
            else:
                print(f"❌ Ключ {key} уже привязан к другому HWID: {hwid_bindings[key]}. Текущий HWID: {hwid}.")
                return JSONResponse(content={"error": "Key already bound to another HWID"}, status_code=403)
        
        # Привязываем ключ к HWID
        hwid_bindings[key] = hwid
        save_hwid_bindings(hwid_bindings)
        
        print(f"✅ Ключ {key} успешно активирован и привязан к HWID: {hwid}.")
        return JSONResponse(content={"status": "ok", "msg": "Key activated successfully"})
    except Exception as e:
        print(f"❌ Критическая ошибка в /activate: {e}")
        return JSONResponse(content={"error": "Внутренняя ошибка сервера"}, status_code=500)

@app.get("/keys")
def list_keys_info():
    try:
        all_keys = load_all_keys()
        hwid_bindings = load_hwid_bindings()
        print(f"✅ Запрос /keys: {len(all_keys)} ключей, {len(hwid_bindings)} привязок.")
        return JSONResponse(content={
            "total_keys_in_file": len(all_keys),
            "activated_keys_count": len(hwid_bindings),
            "activated_keys_details": hwid_bindings
        })
    except Exception as e:
        print(f"❌ Критическая ошибка в /keys: {e}")
        return JSONResponse(content={"error": "Внутренняя ошибка сервера"}, status_code=500)
