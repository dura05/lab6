from flask import Flask, request, jsonify, redirect, render_template
import requests
import threading
import time

app = Flask(__name__)


# это нужно для балансировки нагрузки на сервера
class LoadBalancer:
    def __init__(self):
        self.instances = []
        self.current_index = 0

    # функция для добавления сервера в пул
    def add_instance(self, ip, port):
        instance = {"ip": ip, "port": port, "active": False}
        self.instances.append(instance)
        # При добавлении сервера сразу проверяем его статус
        self.check_instance_health(instance)

    # удаление сервера из пула
    def remove_instance(self, index_inst):
        if 0 <= index_inst < len(self.instances):
            self.instances.pop(index_inst)
            if self.current_index >= len(self.instances):
                self.current_index = 0

    def get_next_instance(self):
        if not self.instances:
            return None
        start_index = self.current_index
        while True:
            instance = self.instances[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.instances)
            if instance["active"]:
                return instance
            if self.current_index == start_index:
                return None

    # статус сервера
    @staticmethod
    def check_instance_health(instance):
        try:
            url = f"http://{instance['ip']}:{instance['port']}/health"
            response = requests.get(url, timeout=3)
            instance["active"] = (response.status_code == 200)
            return instance["active"]
        except requests.exceptions.RequestException:
            instance["active"] = False
            return False

    # чек на статусы всех серверов
    def check_all_instances_health(self):
        for instance in self.instances:
            self.check_instance_health(instance)

    # хэлф чек
    def health_check(self):
        while True:
            self.check_all_instances_health()
            time.sleep(5)
lb = LoadBalancer()

#роуты
@app.route('/')
def index():
    return render_template("index.html", instances=lb.instances)

@app.route('/add_instance', methods=['POST'])
def add_instance():
    ip = request.form['ip']
    port = int(request.form['port'])
    lb.add_instance(ip, port)
    return redirect('/')

@app.route('/remove_instance', methods=['POST'])
def remove_instance():
    index_inst = int(request.form['index'])
    lb.remove_instance(index_inst)
    return redirect('/')


@app.route('/health')
def health():
    lb.check_all_instances_health()
    return jsonify([{
        "ip": i["ip"],
        "port": i["port"],
        "active": i["active"]
    } for i in lb.instances])

@app.route('/process')
def process():
    if not lb.instances:
        return "Нет доступных серверов", 500
    for _ in range(len(lb.instances)):
        instance = lb.get_next_instance()
        if not instance:
            break
        try:
            response = requests.get(
                f"http://{instance['ip']}:{instance['port']}/process",
                timeout=3
            )
            return response.json()
        except requests.exceptions.RequestException:
            instance["active"] = False
            continue

    return "Нет доступных серверов", 500

@app.route('/<path:path>')
def intercept(path):
    if not lb.instances:
        return "Нет доступных серверов", 500

    for _ in range(len(lb.instances)):
        instance = lb.get_next_instance()
        if not instance:
            break
        try:
            response = requests.get(
                f"http://{instance['ip']}:{instance['port']}/{path}",
                timeout=3
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return jsonify({"error": f"Путь не найден на сервере {instance['ip']}:{instance['port']}"})
        except requests.exceptions.RequestException:
            instance["active"] = False
            continue

    return "Нет доступных серверов", 500


if __name__ == '__main__':
    health_thread = threading.Thread(target=lb.health_check, daemon=True)
    health_thread.start()
    app.run(port=5000, debug=True)