from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

API_URL = "https://api.juspay.in/upi/verify-vpa"

@app.route("/api/verify", methods=["GET"])
def verify_vpa():
    vpa = request.args.get("vpa")
    if not vpa:
        return jsonify({"error": "Missing 'vpa' parameter"}), 400

    try:
        res = requests.post(API_URL, data={'vpa': vpa, 'merchant_id': 'milaap'})
        return jsonify({
            "source": "juspay",
            "api_url": API_URL,
            "vpa": vpa,
            "result": res.json()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "UPI verification API is live 🚀"})

if __name__ == "__main__":
    app.run(debug=True)
