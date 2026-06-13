import os
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================
# CONFIG
# ============================================
GSM_API_URL = "https://gsmunlock.net/api/v2"
GSM_API_KEY = os.environ.get("GSM_API_KEY", "Q6S-WEX-FFE-SM0-911-PT4-CKN-WOQ")
BOT_TOKEN   = os.environ.get("BOT_TOKEN", "")
ADMIN_ID    = os.environ.get("ADMIN_ID", "")  # Telegram admin ID

# ============================================
# GSM API HELPER
# ============================================
def gsm_request(action, extra={}):
    payload = {
        "key": GSM_API_KEY,
        "action": action,
        **extra
    }
    try:
        r = requests.post(GSM_API_URL, json=payload, timeout=30)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============================================
# ROUTES
# ============================================

# Health check
@app.route("/")
def index():
    return jsonify({"status": "ok", "service": "KhodjiPro GSM Backend"})

# ============================================
# SERVICES LIST
# ============================================
@app.route("/api/services", methods=["GET"])
def get_services():
    """gsmunlock.net dan barcha IMEI xizmatlarni olish"""
    result = gsm_request("imeiservicelist")
    
    if "status" in result and result["status"] == "error":
        return jsonify({"success": False, "message": result.get("message")}), 500

    services = []
    raw = result if isinstance(result, list) else result.get("services", [])
    
    for svc in raw:
        services.append({
            "id":       svc.get("ServiceID") or svc.get("id"),
            "name":     svc.get("ServiceName") or svc.get("name"),
            "time":     svc.get("TAT") or svc.get("time", ""),
            "price":    svc.get("Price") or svc.get("price", ""),
            "group":    svc.get("GroupName") or svc.get("group", ""),
            "cat":      detect_cat(svc.get("ServiceName","") + " " + svc.get("GroupName","")),
        })

    return jsonify({"success": True, "services": services, "total": len(services)})

def detect_cat(text):
    """Xizmat nomiga qarab kategoriya aniqlash"""
    t = text.lower()
    if "icloud" in t or "fmi" in t or "find my" in t:
        return "icloud"
    if "frp" in t or "google account" in t or "bypass" in t:
        return "frp"
    if "check" in t or "info" in t or "lookup" in t:
        return "check"
    if "remote" in t or "tool" in t or "rent" in t:
        return "remote"
    if "server" in t or "mdm" in t or "unlock" in t:
        return "server"
    return "imei"

# ============================================
# PLACE ORDER
# ============================================
@app.route("/api/order", methods=["POST"])
def place_order():
    """Buyurtma berish"""
    data = request.json
    service_id = data.get("service_id")
    imei       = data.get("imei", "").strip()
    note       = data.get("note", "")
    payment    = data.get("payment", "")
    user_id    = data.get("user_id", "")
    price      = data.get("price", "")
    svc_name   = data.get("service_name", "")

    if not service_id or not imei:
        return jsonify({"success": False, "message": "service_id va imei majburiy"}), 400

    # gsmunlock.net ga buyurtma yuborish
    result = gsm_request("placeimeiorder", {
        "ServiceID": service_id,
        "IMEI":      imei,
        "Reference": f"KP-{user_id}-{int(datetime.now().timestamp())}"
    })

    if result.get("status") == "error":
        return jsonify({"success": False, "message": result.get("message", "Xato yuz berdi")}), 500

    order_id = result.get("OrderID") or result.get("order_id") or f"KP{int(datetime.now().timestamp())}"

    # Admin ga Telegram xabari yuborish
    if BOT_TOKEN and ADMIN_ID:
        notify_admin(order_id, svc_name, imei, price, payment, note, user_id)

    return jsonify({
        "success":  True,
        "order_id": order_id,
        "message":  "Buyurtma muvaffaqiyatli qabul qilindi"
    })

# ============================================
# ORDER STATUS
# ============================================
@app.route("/api/order/<order_id>", methods=["GET"])
def order_status(order_id):
    """Buyurtma holatini tekshirish"""
    result = gsm_request("getimeiorder", {"OrderID": order_id})

    if result.get("status") == "error":
        return jsonify({"success": False, "message": result.get("message")}), 500

    return jsonify({
        "success": True,
        "order":   {
            "id":     order_id,
            "status": result.get("OrderStatus", "pending"),
            "result": result.get("Result", ""),
            "info":   result.get("Information", ""),
        }
    })

# ============================================
# ACCOUNT INFO
# ============================================
@app.route("/api/account", methods=["GET"])
def account_info():
    """API akkaunt ma'lumotlari"""
    result = gsm_request("accountinfo")
    return jsonify({"success": True, "data": result})

# ============================================
# TELEGRAM ADMIN NOTIFY
# ============================================
def notify_admin(order_id, svc_name, imei, price, payment, note, user_id):
    msg = (
        f"🆕 YANGI BUYURTMA\n\n"
        f"📋 Order ID: {order_id}\n"
        f"📱 IMEI: {imei}\n"
        f"🔧 Xizmat: {svc_name}\n"
        f"💰 Narx: {price}\n"
        f"💳 To'lov: {payment}\n"
        f"👤 User: {user_id}\n"
        f"📝 Izoh: {note or '-'}\n"
        f"🕐 Vaqt: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_ID, "text": msg}
        )
    except:
        pass

# ============================================
# RUN
# ============================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
