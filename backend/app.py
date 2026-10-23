from flask import Flask, request, jsonify
import mysql.connector
import os
import time

app = Flask(__name__)


def get_db():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"]
    )


def initialize_database():
    for attempt in range(30):
        try:
            connection = get_db()
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    customer VARCHAR(100) NOT NULL,
                    food VARCHAR(100) NOT NULL,
                    quantity INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
            cursor.close()
            connection.close()
            return
        except mysql.connector.Error:
            time.sleep(2)

    raise RuntimeError("Database did not become ready")


@app.route("/")
def home():
    from flask import send_from_directory
    return send_from_directory("/frontend", "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/orders", methods=["GET"])
def list_orders():
    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, customer, food, quantity, created_at "
            "FROM orders ORDER BY id DESC"
        )
        orders = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(orders)
    except mysql.connector.Error:
        app.logger.exception("Unable to read orders")
        return jsonify({"error": "Database unavailable"}), 503


@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    customer = str(data.get("customer", "")).strip()
    food = str(data.get("food", "")).strip()
    quantity = data.get("quantity")

    if not customer or not food:
        return jsonify({"error": "Customer and food are required"}), 400

    if isinstance(quantity, bool) or not isinstance(quantity, int):
        return jsonify({"error": "Quantity must be an integer"}), 400

    if not 1 <= quantity <= 100:
        return jsonify({"error": "Quantity must be between 1 and 100"}), 400

    try:
        connection = get_db()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO orders (customer, food, quantity) VALUES (%s, %s, %s)",
            (customer, food, quantity)
        )
        connection.commit()
        order_id = cursor.lastrowid
        cursor.close()
        connection.close()
        return jsonify({"message": "Order placed", "order_id": order_id}), 201
    except mysql.connector.Error:
        app.logger.exception("Unable to save order")
        return jsonify({"error": "Database unavailable"}), 503


if __name__ == "__main__":
    initialize_database()
    app.run(host="0.0.0.0", port=5000)
