import socket
import threading
import time
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

from remote_core import build_message, is_valid_port, normalize_host


class AnesDeskMobileApp(App):
    def build(self):
        self.server_socket = None
        self.client_socket = None
        self.is_server_running = False
        self.is_client_running = False
        self.log_lines = []

        root = BoxLayout(orientation="vertical", padding=12, spacing=12)

        title = Label(text="AnesDesk Mobile", font_size=24, bold=True, size_hint_y=None, height=40)
        root.add_widget(title)

        info = Label(
            text="Usa la misma IP y puerto para conectar PC, móvil o tablet.\nFunciona en LAN y en redes compatibles.",
            size_hint_y=None,
            height=72,
            text_size=(None, None),
        )
        root.add_widget(info)

        form = BoxLayout(size_hint_y=None, height=110, spacing=8)
        form.orientation = "vertical"

        self.host_input = TextInput(text="192.168.1.10", multiline=False, hint_text="IP del anfitrión")
        form.add_widget(self.host_input)
        self.port_input = TextInput(text="9999", multiline=False, hint_text="Puerto")
        form.add_widget(self.port_input)
        root.add_widget(form)

        buttons = BoxLayout(size_hint_y=None, height=48, spacing=8)
        self.server_button = ToggleButton(text="Iniciar servidor", group="mode")
        self.server_button.bind(on_press=self.toggle_server)
        buttons.add_widget(self.server_button)

        self.client_button = ToggleButton(text="Conectar", group="mode")
        self.client_button.bind(on_press=self.toggle_client)
        buttons.add_widget(self.client_button)
        root.add_widget(buttons)

        self.message_input = TextInput(text="hola", multiline=False, hint_text="Mensaje")
        root.add_widget(self.message_input)

        self.send_button = Button(text="Enviar mensaje")
        self.send_button.bind(on_press=self.send_message)
        root.add_widget(self.send_button)

        self.log_label = Label(text="Esperando conexión...", size_hint_y=None, height=220, text_size=(None, None), valign="top")
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.log_label)
        root.add_widget(scroll)

        self.log("Aplicación lista. Usa la IP y puerto del equipo anfitrión.")
        return root

    def log(self, message):
        self.log_lines.append(f"[{time.strftime('%H:%M:%S')}] {message}")
        if len(self.log_lines) > 20:
            self.log_lines = self.log_lines[-20:]
        self.log_label.text = "\n".join(self.log_lines)

    def toggle_server(self, instance):
        if self.is_server_running:
            self.is_server_running = False
            if self.server_socket:
                try:
                    self.server_socket.close()
                except Exception:
                    pass
            self.server_button.text = "Iniciar servidor"
            self.log("Servidor detenido.")
            return

        if not is_valid_port(self.port_input.text):
            self.log("Puerto inválido.")
            return

        self.is_server_running = True
        self.server_button.text = "Detener servidor"
        threading.Thread(target=self.run_server, daemon=True).start()

    def run_server(self):
        port = int(self.port_input.text)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind(("0.0.0.0", port))
            self.server_socket.listen(1)
            self.log(f"Servidor escuchando en puerto {port}.")
            while self.is_server_running:
                try:
                    conn, addr = self.server_socket.accept()
                    self.client_socket = conn
                    self.log(f"Conectado desde {addr}")
                    threading.Thread(target=self.handle_connection, args=(conn,), daemon=True).start()
                except OSError:
                    break
        except Exception as exc:
            self.log(f"Error en servidor: {exc}")

    def handle_connection(self, conn):
        while self.is_server_running:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                text = data.decode("utf-8", errors="ignore").strip()
                self.log(f"Recibido: {text}")
                conn.sendall(build_message("TEXT", "ack"))
            except Exception as exc:
                self.log(f"Conexión cerrada: {exc}")
                break

    def toggle_client(self, instance):
        if self.is_client_running:
            self.is_client_running = False
            if self.client_socket:
                try:
                    self.client_socket.close()
                except Exception:
                    pass
            self.client_button.text = "Conectar"
            self.log("Desconectado.")
            return

        if not is_valid_port(self.port_input.text):
            self.log("Puerto inválido.")
            return

        self.is_client_running = True
        self.client_button.text = "Desconectar"
        threading.Thread(target=self.run_client, daemon=True).start()

    def run_client(self):
        host = normalize_host(self.host_input.text)
        port = int(self.port_input.text)
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            self.log(f"Conectado a {host}:{port}")
            self.send_message(None)
        except Exception as exc:
            self.log(f"No se pudo conectar: {exc}")
            self.is_client_running = False
            self.client_button.text = "Conectar"

    def send_message(self, instance):
        if self.client_socket is None:
            self.log("No hay conexión activa.")
            return
        try:
            message = self.message_input.text.strip() or "ping"
            self.client_socket.sendall(build_message("TEXT", message))
            self.log(f"Enviado: {message}")
        except Exception as exc:
            self.log(f"Error al enviar: {exc}")


if __name__ == "__main__":
    AnesDeskMobileApp().run()
