from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import pytz
import os
import json

app = Flask(__name__)

# Railway-friendly SQLite config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///signals.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------- DATABASE MODEL --------------------
class Signal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(50))
    event = db.Column(db.String(10))      # buy / sell
    buy_price = db.Column(db.Float, nullable=True)
    sell_price = db.Column(db.Float, nullable=True)
    time = db.Column(db.String(50))

with app.app_context():
    db.create_all()

# -------------------- HOME --------------------
@app.route('/')
def home():
    return '''
    <html>
    <head><title>TradingView Webhook</title></head>
    <body style="font-family: Arial; text-align:center; padding-top:80px;">
        <h1>🚀 TradingView Webhook Receiver</h1>
        <p>POST webhook to <b>/webhook</b></p>
        <p>View signals at <a href="/signals" target="_blank">/signals</a></p>
    </body>
    </html>
    '''

# -------------------- WEBHOOK --------------------
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = json.loads(request.data.decode('utf-8'))

        symbol = data.get("symbol")
        event = data.get("event").lower()
        price = float(data.get("price"))
        time_raw = data.get("time")

        # ----- Time handling -----
        if isinstance(time_raw, int):
            utc_time = datetime.utcfromtimestamp(time_raw / 1000)
            utc_time = pytz.utc.localize(utc_time)
        else:
            utc_time = datetime.strptime(time_raw, "%Y-%m-%dT%H:%M:%SZ")
            utc_time = pytz.utc.localize(utc_time)

        ist_time = utc_time.astimezone(pytz.timezone("Asia/Kolkata"))
        time_str = ist_time.strftime("%d-%m-%Y %H:%M:%S")

        # ----- Assign prices -----
        buy_price = price if event == "buy" else None
        sell_price = price if event == "sell" else None

        signal = Signal(
            symbol=symbol,
            event=event,
            buy_price=buy_price,
            sell_price=sell_price,
            time=time_str
        )

        db.session.add(signal)
        db.session.commit()

        print(f"🔔 {event.upper()} | {symbol} | {price} | {time_str}")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------- VIEW SIGNALS --------------------
@app.route('/signals', methods=['GET', 'POST'])
def view_signals():
    if request.method == 'POST':
        Signal.query.delete()
        db.session.commit()
        return redirect(url_for('view_signals'))

    signals = Signal.query.all()

    html = '''
    <html>
    <head>
        <title>Signals</title>
        <style>
            body { font-family: Arial; text-align:center; background:#f9f9f9; }
            table { border-collapse: collapse; width: 90%; margin:auto; }
            th, td { border: 1px solid #ccc; padding: 8px; }
            th { background: #eee; }
            .buy { color: green; font-weight: bold; }
            .sell { color: red; font-weight: bold; }
            button { background:red; color:white; padding:10px 20px; border:none; }
        </style>
    </head>
    <body>
        <h1>📊 Trading Signals</h1>
        <form method="post" onsubmit="return confirm('Delete all records?');">
            <button type="submit">Delete All</button>
        </form>
        <table>
            <tr>
                <th>ID</th>
                <th>Symbol</th>
                <th>Event</th>
                <th>Buy Price</th>
                <th>Sell Price</th>
                <th>Time (IST)</th>
            </tr>
            {% for s in signals %}
            <tr>
                <td>{{ s.id }}</td>
                <td>{{ s.symbol }}</td>
                <td class="{{ s.event }}">{{ s.event }}</td>
                <td>{{ s.buy_price if s.buy_price else '' }}</td>
                <td>{{ s.sell_price if s.sell_price else '' }}</td>
                <td>{{ s.time }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    return render_template_string(html, signals=signals)

# -------------------- RUN --------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
