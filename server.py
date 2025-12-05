from flask import Flask, jsonify
import sys

app = Flask(__name__)


@app.route('/health') #эндпоинт состояния
def health():
    return jsonify({
        "status": "ОК",
        "port": port
    })


@app.route('/process') #возврат порта
def process():
    return jsonify({
        "message": "Запрос обработан",
        "port": port
    })


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Используй команду: python server.py <порт>")
        sys.exit(1)

    port = int(sys.argv[1])
    app.run(port=port)