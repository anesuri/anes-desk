import socket
import threading
import time
import zlib
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk

try:
    from mss import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

from remote_core import get_resolution, is_valid_port, normalize_host, quality_to_scale


class AnesDeskProApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AnesDesk Pro")
        self.root.geometry("1180x760")
        self.root.minsize(1024, 680)
        self.root.configure(bg="#07111f")

        self.server_socket = None
        self.client_socket = None
        self.is_server_running = False
        self.is_client_running = False
        self.status_mode = "idle"
        self.status_pulse = 0

        self.server_port_var = tk.StringVar(value="9999")
        self.client_port_var = tk.StringVar(value="9999")
        self.client_host_var = tk.StringVar(value="127.0.0.1")
        self.nickname_var = tk.StringVar(value="AnesDesk Host")
        self.mode_var = tk.StringVar(value="Remote Control")
        self.quality_var = tk.StringVar(value="Balanced")
        self.fps_var = tk.StringVar(value="15")
        self.scale_var = tk.StringVar(value="85%")
        self.compress_var = tk.BooleanVar(value=True)
        self.reconnect_var = tk.BooleanVar(value=True)
        self.chat_text_var = tk.StringVar(value="")

        self.setup_ui()
        self.update_status_animation()

    def setup_ui(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#07111f")
        style.configure("TLabel", background="#07111f", foreground="#e6f2ff")
        style.configure("TButton", padding=6)
        style.configure("Card.TLabelframe", background="#0f1b2d", foreground="#f3f8ff")
        style.configure("Card.TLabelframe.Label", background="#0f1b2d", foreground="#f3f8ff")
        style.configure("Info.TLabel", background="#0f1b2d", foreground="#9fc2ff")

        self.root.option_add("*Font", "Segoe UI 10")

        header = ttk.Frame(self.root, padding=20)
        header.pack(fill="x")
        ttk.Label(header, text="AnesDesk Pro", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(header, text="Control remoto moderno, rápido y adaptable para PC, móvil y tablet.", style="Info.TLabel").pack(anchor="w", pady=(4, 0))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.tab_server = ttk.Frame(self.notebook, padding=12)
        self.tab_client = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_server, text="🖥️ Servidor / Compartir")
        self.notebook.add(self.tab_client, text="🎮 Cliente / Controlar")

        self.build_server_tab()
        self.build_client_tab()

    def build_server_tab(self):
        left = ttk.LabelFrame(self.tab_server, text="Configuración del anfitrión", padding=16, style="Card.TLabelframe")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        left.columnconfigure(0, weight=1)

        right = ttk.LabelFrame(self.tab_server, text="Estado de sesión", padding=16, style="Card.TLabelframe")
        right.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        right.columnconfigure(0, weight=1)

        self.tab_server.rowconfigure(0, weight=1)
        self.tab_server.columnconfigure(0, weight=1)
        self.tab_server.columnconfigure(1, weight=1)

        ip_local = self.get_local_ip()
        ttk.Label(left, text=f"IP local: {ip_local}", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(left, text="Comparte esta IP, el puerto y el modo de sesión para conectar desde otros dispositivos.", wraplength=320, style="Info.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 12))

        ttk.Label(left, text="Apodo de sesión").grid(row=2, column=0, sticky="w")
        ttk.Entry(left, textvariable=self.nickname_var).grid(row=3, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(left, text="Puerto").grid(row=4, column=0, sticky="w")
        ttk.Entry(left, textvariable=self.server_port_var).grid(row=5, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(left, text="Modo").grid(row=6, column=0, sticky="w")
        ttk.Combobox(left, textvariable=self.mode_var, state="readonly", values=["Remote Control", "Screen Share", "File Transfer", "Quick Chat"]).grid(row=7, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(left, text="Calidad").grid(row=8, column=0, sticky="w")
        ttk.Combobox(left, textvariable=self.quality_var, state="readonly", values=["Low", "Balanced", "High"]).grid(row=9, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(left, text="FPS").grid(row=10, column=0, sticky="w")
        ttk.Combobox(left, textvariable=self.fps_var, state="readonly", values=["10", "15", "25"]).grid(row=11, column=0, sticky="ew", pady=(0, 8))

        self.server_toggle = ttk.Button(left, text="Iniciar sesión", command=self.toggle_server)
        self.server_toggle.grid(row=12, column=0, sticky="ew", pady=(10, 8))

        self.server_checkbox_frame = ttk.Frame(left)
        self.server_checkbox_frame.grid(row=13, column=0, sticky="w", pady=(4, 6))
        ttk.Checkbutton(self.server_checkbox_frame, text="Compresión activa", variable=self.compress_var).pack(side="left")
        ttk.Checkbutton(self.server_checkbox_frame, text="Reconexión automática", variable=self.reconnect_var).pack(side="left", padx=(10, 0))

        ttk.Label(left, text="Registro del servidor", font=("Segoe UI", 10, "bold")).grid(row=14, column=0, sticky="w", pady=(10, 4))
        self.server_log = tk.Text(left, height=9, bg="#0f1b2d", fg="#e6f2ff", insertbackground="white")
        self.server_log.grid(row=15, column=0, sticky="nsew")

        self.led_canvas = tk.Canvas(right, width=90, height=90, bg="#0f1b2d", highlightthickness=0)
        self.led_canvas.grid(row=0, column=0, pady=(0, 8))
        ttk.Label(right, text="Sesión lista para compartir", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, sticky="w")
        self.server_status_label = ttk.Label(right, text="Esperando conexión", style="Info.TLabel")
        self.server_status_label.grid(row=2, column=0, sticky="w", pady=(6, 10))

        self.metrics_text = tk.Text(right, height=8, bg="#0f1b2d", fg="#93c5fd", insertbackground="white")
        self.metrics_text.grid(row=3, column=0, sticky="nsew")
        self.metrics_text.insert("end", "• Modo: Remote Control\n• Calidad: Balanced\n• FPS objetivo: 15\n• Estado: Inactivo\n")
        self.metrics_text.configure(state="disabled")

    def build_client_tab(self):
        left = ttk.LabelFrame(self.tab_client, text="Conexión remota", padding=16, style="Card.TLabelframe")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        left.columnconfigure(0, weight=1)

        right = ttk.LabelFrame(self.tab_client, text="Vista remota", padding=12, style="Card.TLabelframe")
        right.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.tab_client.rowconfigure(0, weight=1)
        self.tab_client.columnconfigure(0, weight=1)
        self.tab_client.columnconfigure(1, weight=2)

        ttk.Label(left, text="IP remota").grid(row=0, column=0, sticky="w")
        ttk.Entry(left, textvariable=self.client_host_var).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(left, text="Puerto").grid(row=2, column=0, sticky="w")
        ttk.Entry(left, textvariable=self.client_port_var).grid(row=3, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(left, text="Modo").grid(row=4, column=0, sticky="w")
        ttk.Combobox(left, textvariable=self.mode_var, state="readonly", values=["Remote Control", "Screen Share", "File Transfer", "Quick Chat"]).grid(row=5, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(left, text="Calidad").grid(row=6, column=0, sticky="w")
        ttk.Combobox(left, textvariable=self.quality_var, state="readonly", values=["Low", "Balanced", "High"]).grid(row=7, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(left, text="Escala").grid(row=8, column=0, sticky="w")
        ttk.Combobox(left, textvariable=self.scale_var, state="readonly", values=["60%", "85%", "100%", "120%"]).grid(row=9, column=0, sticky="ew", pady=(0, 8))

        self.btn_connect = ttk.Button(left, text="Conectar", command=self.toggle_client)
        self.btn_connect.grid(row=10, column=0, sticky="ew", pady=(10, 8))

        self.client_chat_entry = ttk.Entry(left, textvariable=self.chat_text_var)
        self.client_chat_entry.grid(row=11, column=0, sticky="ew", pady=(6, 4))
        ttk.Button(left, text="Enviar mensaje", command=self.send_chat_message).grid(row=12, column=0, sticky="ew")

        self.client_log = tk.Text(left, height=8, bg="#0f1b2d", fg="#e6f2ff", insertbackground="white")
        self.client_log.grid(row=13, column=0, sticky="nsew", pady=(10, 0))
        self.client_log.insert("end", "Conecta a un anfitrión para ver la sesión remota.\n")
        self.client_log.configure(state="disabled")

        self.canvas = tk.Canvas(right, bg="black", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Motion>", self.send_mouse_move)
        self.canvas.bind("<Button-1>", lambda e: self.send_mouse_click(e, "left"))
        self.canvas.bind("<Button-3>", lambda e: self.send_mouse_click(e, "right"))

        self.canvas_text = ttk.Label(right, text="Vista previa remota", style="Info.TLabel")
        self.canvas_text.grid(row=1, column=0, sticky="w", pady=(8, 0))

    def log_server(self, msg):
        self.server_log.config(state="normal")
        self.server_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.server_log.see("end")
        self.server_log.config(state="disabled")

    def log_client(self, msg):
        self.client_log.config(state="normal")
        self.client_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.client_log.see("end")
        self.client_log.config(state="disabled")

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def update_metrics(self, message):
        self.metrics_text.configure(state="normal")
        self.metrics_text.delete("1.0", "end")
        self.metrics_text.insert("end", f"• Modo: {self.mode_var.get()}\n")
        self.metrics_text.insert("end", f"• Calidad: {self.quality_var.get()}\n")
        self.metrics_text.insert("end", f"• FPS: {self.fps_var.get()}\n")
        self.metrics_text.insert("end", f"• Escala: {self.scale_var.get()}\n")
        self.metrics_text.insert("end", f"• Estado: {message}\n")
        self.metrics_text.configure(state="disabled")

    def set_status(self, message, active):
        color = "#22c55e" if active else "#ef4444"
        self.status_mode = "active" if active else "idle"
        self.server_status_label.config(text=message)
        self.draw_led(color)
        self.update_metrics(message)

    def draw_led(self, color):
        self.led_canvas.delete("all")
        self.led_canvas.create_oval(10, 10, 80, 80, fill=color, outline="#ffffff", width=2)
        self.led_canvas.create_oval(22, 22, 68, 68, fill="#ffffff", outline="")

    def update_status_animation(self):
        if self.status_mode == "active":
            pulse = "#4ade80" if self.status_pulse % 2 == 0 else "#86efac"
        else:
            pulse = "#ef4444" if self.status_pulse % 2 == 0 else "#fca5a5"
        self.draw_led(pulse)
        self.status_pulse = (self.status_pulse + 1) % 4
        self.root.after(500, self.update_status_animation)

    def toggle_server(self):
        if not is_valid_port(self.server_port_var.get()):
            messagebox.showerror("Puerto inválido", "Introduce un valor entre 1 y 65535.")
            return
        if not self.is_server_running:
            self.is_server_running = True
            self.server_toggle.config(text="Detener sesión")
            self.set_status("Sesión activa y lista para conexiones", True)
            self.log_server("Servidor activado con un diseño profesional y opciones avanzadas.")
            threading.Thread(target=self.run_server, daemon=True).start()
        else:
            self.is_server_running = False
            if self.server_socket:
                try:
                    self.server_socket.close()
                except Exception:
                    pass
            self.server_toggle.config(text="Iniciar sesión")
            self.set_status("Sesión detenida", False)
            self.log_server("Servidor detenido.")

    def run_server(self):
        port = int(self.server_port_var.get())
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind(("0.0.0.0", port))
            self.server_socket.listen(4)
            self.log_server(f"Servidor listo en {port} para una sesión {self.mode_var.get().lower()}.")
            while self.is_server_running:
                try:
                    conn, addr = self.server_socket.accept()
                    self.log_server(f"Conexión establecida con {addr}")
                    self.set_status(f"Conectado a {addr}", True)
                    threading.Thread(target=self.stream_screen, args=(conn,), daemon=True).start()
                    threading.Thread(target=self.receive_commands, args=(conn,), daemon=True).start()
                except OSError:
                    break
        except Exception as exc:
            self.log_server(f"Error en servidor: {exc}")
            self.toggle_server()

    def stream_screen(self, conn):
        if not MSS_AVAILABLE:
            self.log_server("Instala 'mss' para capturar pantalla con fluidez.")
            return

        with mss() as sct:
            monitor = sct.monitors[1]
            try:
                while self.is_server_running:
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
                    target_w, target_h = get_resolution(img.size, quality_to_scale(self.quality_var.get()))
                    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    raw_bytes = img.tobytes()
                    compressed = zlib.compress(raw_bytes) if self.compress_var.get() else raw_bytes
                    header = f"{target_w},{target_h},{len(compressed)}:".encode("utf-8")
                    conn.sendall(header + compressed)
                    time.sleep(max(0.001, 1 / max(1, int(self.fps_var.get()))))
            except Exception:
                self.log_server("La sesión remota ha finalizado.")

    def receive_commands(self, conn):
        buffer = ""
        while self.is_server_running:
            try:
                data = conn.recv(2048).decode("utf-8")
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.execute_command(line)
            except Exception:
                break

    def execute_command(self, cmd_str):
        if not PYAUTOGUI_AVAILABLE:
            return
        try:
            parts = cmd_str.split(":")
            cmd = parts[0]
            if cmd == "MOVE":
                x, y = float(parts[1]), float(parts[2])
                sw, sh = pyautogui.size()
                pyautogui.moveTo(int(x * sw), int(y * sh))
            elif cmd == "CLICK":
                btn = parts[1]
                pyautogui.click(button=btn)
            elif cmd == "CHAT":
                message = parts[1] if len(parts) > 1 else ""
                self.log_server(f"Mensaje recibido: {message}")
        except Exception:
            pass

    def toggle_client(self):
        if not is_valid_port(self.client_port_var.get()):
            messagebox.showerror("Puerto inválido", "Introduce un valor entre 1 y 65535.")
            return
        if not self.is_client_running:
            self.is_client_running = True
            self.btn_connect.config(text="Desconectar")
            self.log_client("Estableciendo conexión con el anfitrión...")
            threading.Thread(target=self.run_client, daemon=True).start()
        else:
            self.is_client_running = False
            if self.client_socket:
                try:
                    self.client_socket.close()
                except Exception:
                    pass
            self.btn_connect.config(text="Conectar")
            self.log_client("Conexión cerrada.")

    def run_client(self):
        ip = normalize_host(self.client_host_var.get())
        port = int(self.client_port_var.get())
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((ip, port))
            self.log_client(f"Conectado a {ip}:{port}")
            self.canvas_text.config(text="Vista remota en vivo")
        except Exception as exc:
            self.log_client(f"No se pudo conectar: {exc}")
            self.is_client_running = False
            self.btn_connect.config(text="Conectar")
            return

        buffer = bytearray()
        while self.is_client_running:
            try:
                chunk = self.client_socket.recv(8192)
                if not chunk:
                    break
                buffer.extend(chunk)
                while b":" in buffer:
                    header_end = buffer.find(b":")
                    header = buffer[:header_end].decode("utf-8")
                    try:
                        w, h, size = map(int, header.split(","))
                    except ValueError:
                        buffer = buffer[header_end + 1 :]
                        continue
                    if len(buffer) >= header_end + 1 + size:
                        img_data = buffer[header_end + 1 : header_end + 1 + size]
                        buffer = buffer[header_end + 1 + size :]
                        raw = zlib.decompress(img_data) if self.compress_var.get() else img_data
                        img = Image.frombytes("RGB", (w, h), raw)
                        self.update_canvas_image(img)
                    else:
                        break
            except Exception:
                break

        self.toggle_client()

    def update_canvas_image(self, img):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw > 10 and ch > 10:
            img_resized = img.resize((cw, ch), Image.Resampling.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(img_resized)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")

    def send_mouse_move(self, event):
        if self.is_client_running and self.client_socket:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            if cw > 0 and ch > 0:
                rel_x = event.x / cw
                rel_y = event.y / ch
                try:
                    self.client_socket.sendall(f"MOVE:{rel_x}:{rel_y}\n".encode("utf-8"))
                except Exception:
                    pass

    def send_mouse_click(self, event, button):
        if self.is_client_running and self.client_socket:
            try:
                self.client_socket.sendall(f"CLICK:{button}\n".encode("utf-8"))
            except Exception:
                pass

    def send_chat_message(self):
        message = self.chat_text_var.get().strip()
        if not message:
            return
        if self.is_client_running and self.client_socket:
            try:
                self.client_socket.sendall(f"CHAT:{message}\n".encode("utf-8"))
                self.log_client(f"Tú: {message}")
            except Exception as exc:
                self.log_client(f"No se pudo enviar: {exc}")
        else:
            self.log_client("Conecta primero para enviar un mensaje.")
        self.chat_text_var.set("")


if __name__ == "__main__":
    root = tk.Tk()
    app = AnesDeskProApp(root)
    root.mainloop()
