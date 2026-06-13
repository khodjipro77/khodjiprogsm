import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from supabase import create_client

app = Flask(__name__)
CORS(app)

# ============================================
# CONFIG
# ============================================
GSM_API_URL   = os.environ.get("GSM_API_URL", "https://gsmunlock.net/api/v2")
GSM_API_KEY   = os.environ.get("GSM_API_KEY", "")
BOT_TOKEN     = os.environ.get("BOT_TOKEN", "")
ADMIN_ID      = os.environ.get("ADMIN_ID", "")
SUPABASE_URL  = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY  = os.environ.get("SUPABASE_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# ============================================
# HELPER
# ============================================
def gsm_request(action, extra={}):
    payload = {"key": GSM_API_KEY, "action": action, **extra}
    try:
        r = requests.post(GSM_API_URL, json=payload, timeout=30)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def notify_admin(order_id, svc_name, imei, price, payment, note, user_email):
    msg = (
        f"🆕 YANGI BUYURTMA\n\n"
        f"📋 Order ID: {order_id}\n"
        f"📱 IMEI: {imei}\n"
        f"🔧 Xizmat: {svc_name}\n"
        f"💰 Narx: {price}\n"
        f"💳 To'lov: {payment}\n"
        f"👤 User: {user_email}\n"
        f"📝 Izoh: {note or '-'}\n"
        f"🕐 Vaqt: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_ID, "text": msg},
            timeout=10
        )
    except:
        pass

# ============================================
# ROUTES
# ============================================
@app.route("/")
def index():
    return jsonify({"status": "ok", "service": "KhodjiPro GSM Backend"})

# SERVICES
@app.route("/api/services")
def get_services():
    result = gsm_request("imeiservicelist")
    if isinstance(result, dict) and result.get("status") == "error":
        return jsonify({"success": False, "message": result.get("message")}), 500
    raw = result if isinstance(result, list) else result.get("services", [])
    services = []
    for svc in raw:
        name = svc.get("ServiceName") or svc.get("name", "")
        group = svc.get("GroupName") or svc.get("group", "")
        services.append({
            "id":    svc.get("ServiceID") or svc.get("id"),
            "name":  name,
            "time":  svc.get("TAT") or svc.get("time", ""),
            "price": svc.get("Price") or svc.get("price", ""),
            "group": group,
            "cat":   detect_cat(name + " " + group),
        })
    return jsonify({"success": True, "services": services, "total": len(services)})

def detect_cat(text):
    t = text.lower()
    if "icloud" in t or "fmi" in t: return "icloud"
    if "frp" in t or "bypass" in t: return "frp"
    if "check" in t or "info" in t: return "check"
    if "remote" in t or "tool" in t or "rent" in t: return "remote"
    if "server" in t or "mdm" in t: return "server"
    return "imei"

# REGISTER
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    if not email or not password or not name:
        return jsonify({"success": False, "message": "Barcha maydonlarni to'ldiring"}), 400
    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"name": name}}
        })
        if res.user:
            return jsonify({"success": True, "message": "Ro'yxatdan o'tdingiz! Email tasdiqlang."})
        return jsonify({"success": False, "message": "Xato yuz berdi"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

# LOGIN
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "")
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            # Profil olish
            profile = supabase.table("profiles").select("*").eq("id", res.user.id).single().execute()
            return jsonify({
                "success": True,
                "token": res.session.access_token,
                "user": {
                    "id": res.user.id,
                    "email": res.user.email,
                    "name": profile.data.get("name", ""),
                    "balance": profile.data.get("balance", 0),
                    "total_orders": profile.data.get("total_orders", 0),
                }
            })
        return jsonify({"success": False, "message": "Email yoki parol noto'g'ri"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": "Email yoki parol noto'g'ri"}), 401

# PROFILE
@app.route("/api/profile", methods=["GET"])
def get_profile():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        user = supabase.auth.get_user(token)
        profile = supabase.table("profiles").select("*").eq("id", user.user.id).single().execute()
        return jsonify({"success": True, "user": profile.data})
    except Exception as e:
        return jsonify({"success": False, "message": "Token noto'g'ri"}), 401

# ORDER HISTORY
@app.route("/api/orders", methods=["GET"])
def get_orders():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        user = supabase.auth.get_user(token)
        orders = supabase.table("orders").select("*").eq("user_id", user.user.id).order("created_at", desc=True).execute()
        return jsonify({"success": True, "orders": orders.data})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 401

# PLACE ORDER
@app.route("/api/order", methods=["POST"])
def place_order():
    data = request.json
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    service_id  = data.get("service_id")
    imei        = data.get("imei", "").strip()
    note        = data.get("note", "")
    payment     = data.get("payment", "")
    price       = float(data.get("price_num", 0))
    svc_name    = data.get("service_name", "")

    if not imei or not service_id:
        return jsonify({"success": False, "message": "IMEI va xizmat majburiy"}), 400

    user_id = None
    user_email = "guest"

    # Token bo'lsa foydalanuvchini aniqla
    if token:
        try:
            user = supabase.auth.get_user(token)
            user_id = user.user.id
            user_email = user.user.email

            # Balansni tekshir
            profile = supabase.table("profiles").select("balance").eq("id", user_id).single().execute()
            balance = float(profile.data.get("balance", 0))
            if balance < price:
                return jsonify({"success": False, "message": "Balans yetarli emas"}), 400

            # Balansdan ayir
            supabase.table("profiles").update({"balance": balance - price}).eq("id", user_id).execute()
        except:
            pass

    # GSM API ga yuborish
    order_id = f"KP{int(datetime.now().timestamp())}"
    gsm_result = gsm_request("placeimeiorder", {
        "ServiceID": service_id,
        "IMEI": imei,
        "Reference": order_id
    })

    if gsm_result.get("OrderID"):
        order_id = str(gsm_result["OrderID"])

    # Supabase ga saqlash
    if supabase and user_id:
        try:
            supabase.table("orders").insert({
                "order_id": order_id,
                "user_id": user_id,
                "service_id": str(service_id),
                "service_name": svc_name,
                "imei": imei,
                "note": note,
                "payment_method": payment,
                "price": price,
                "status": "pending"
            }).execute()
            # Total orders yangilash
            supabase.table("profiles").update({"total_orders": profile.data.get("total_orders", 0) + 1}).eq("id", user_id).execute()
            # Transaction saqlash
            supabase.table("transactions").insert({
                "user_id": user_id,
                "amount": -price,
                "type": "order",
                "description": svc_name
            }).execute()
        except Exception as e:
            print(f"DB error: {e}")

    # Admin xabarnoma
    if BOT_TOKEN and ADMIN_ID:
        notify_admin(order_id, svc_name, imei, price, payment, note, user_email)

    return jsonify({"success": True, "order_id": order_id, "message": "Buyurtma qabul qilindi!"})

# ADD BALANCE (admin qo'lda qo'shadi)
@app.route("/api/balance/add", methods=["POST"])
def add_balance():
    # Faqat admin token bilan
    admin_token = request.headers.get("X-Admin-Token", "")
    if admin_token != os.environ.get("ADMIN_TOKEN", ""):
        return jsonify({"success": False, "message": "Ruxsat yo'q"}), 403

    data = request.json
    email = data.get("email")
    amount = float(data.get("amount", 0))

    try:
        profile = supabase.table("profiles").select("*").eq("email", email).single().execute()
        new_balance = float(profile.data["balance"]) + amount
        supabase.table("profiles").update({"balance": new_balance}).eq("email", email).execute()
        supabase.table("transactions").insert({
            "user_id": profile.data["id"],
            "amount": amount,
            "type": "topup",
            "description": "Admin tomonidan qo'shildi"
        }).execute()
        return jsonify({"success": True, "new_balance": new_balance})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

# ORDER STATUS
@app.route("/api/order/<order_id>", methods=["GET"])
def order_status(order_id):
    result = gsm_request("getimeiorder", {"OrderID": order_id})
    status = result.get("OrderStatus", "pending")
    result_text = result.get("Result", "")
    # Supabase yangilash
    if supabase:
        try:
            supabase.table("orders").update({
                "status": status.lower(),
                "result": result_text,
                "updated_at": datetime.now().isoformat()
            }).eq("order_id", order_id).execute()
        except:
            pass
    return jsonify({"success": True, "status": status, "result": result_text})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
