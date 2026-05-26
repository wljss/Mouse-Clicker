import customtkinter as ctk
import threading
import time
from pynput import mouse as pynput_mouse
from pynput import keyboard as pynput_keyboard

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

BUTTON_MAP = {
    "左键": pynput_mouse.Button.left,
    "右键": pynput_mouse.Button.right,
    "中键": pynput_mouse.Button.middle,
}


class MouseClicker:
    def __init__(self):
        self.clicking = False
        self.mouse_controller = pynput_mouse.Controller()
        self.stop_event = threading.Event()
        self.capturing = False

        self._build_ui()
        self._start_hotkey_listener()

    # ─────────────────── UI 构建 ───────────────────

    def _build_ui(self):
        self.window = ctk.CTk()
        self.window.title("鼠标连点器")
        self.window.geometry("420x540")
        self.window.resizable(False, False)

        # 标题
        ctk.CTkLabel(
            self.window, text="鼠标连点器",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(20, 12))

        # ── 模式选择 ──
        self.mode_var = ctk.StringVar(value="follow")
        frame = ctk.CTkFrame(self.window)
        frame.pack(pady=5, padx=30, fill="x")
        ctk.CTkLabel(frame, text="点击模式:").pack(side="left", padx=(10, 10))
        ctk.CTkRadioButton(
            frame, text="跟随光标", variable=self.mode_var, value="follow",
            command=self._on_mode_change,
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            frame, text="固定坐标", variable=self.mode_var, value="fixed",
            command=self._on_mode_change,
        ).pack(side="left", padx=5)

        # ── 坐标输入 ──
        self.coord_frame = ctk.CTkFrame(self.window)
        self.coord_frame.pack(pady=5, padx=30, fill="x")
        ctk.CTkLabel(self.coord_frame, text="目标坐标:").pack(side="left", padx=(10, 10))
        self.x_entry = ctk.CTkEntry(self.coord_frame, width=75, placeholder_text="X")
        self.x_entry.pack(side="left", padx=3)
        self.y_entry = ctk.CTkEntry(self.coord_frame, width=75, placeholder_text="Y")
        self.y_entry.pack(side="left", padx=3)
        self.capture_btn = ctk.CTkButton(
            self.coord_frame, text="捕获位置", width=80, command=self._start_capture,
        )
        self.capture_btn.pack(side="left", padx=5)
        self._set_coord_state("disabled")

        # ── 点击间隔 ──
        frame = ctk.CTkFrame(self.window)
        frame.pack(pady=5, padx=30, fill="x")
        ctk.CTkLabel(frame, text="点击间隔:").pack(side="left", padx=(10, 10))
        self.speed_var = ctk.IntVar(value=100)
        self.speed_label = ctk.CTkLabel(frame, text="100 ms", width=55)
        self.speed_label.pack(side="right", padx=(0, 10))
        ctk.CTkSlider(
            frame, from_=10, to=1000, number_of_steps=198,
            variable=self.speed_var, command=self._on_speed_change,
        ).pack(side="right", fill="x", expand=True, padx=(0, 5))

        # ── 鼠标按键 ──
        frame = ctk.CTkFrame(self.window)
        frame.pack(pady=5, padx=30, fill="x")
        ctk.CTkLabel(frame, text="鼠标按键:").pack(side="left", padx=(10, 10))
        self.button_var = ctk.StringVar(value="左键")
        ctk.CTkOptionMenu(
            frame, values=["左键", "右键", "中键"], variable=self.button_var,
        ).pack(side="left", padx=5)

        # ── 限制方式 ──
        frame = ctk.CTkFrame(self.window)
        frame.pack(pady=5, padx=30, fill="x")
        ctk.CTkLabel(frame, text="限制方式:").pack(side="left", padx=(10, 10))
        self.limit_var = ctk.StringVar(value="none")
        ctk.CTkRadioButton(
            frame, text="无限制", variable=self.limit_var, value="none",
            command=self._on_limit_change,
        ).pack(side="left", padx=2)
        ctk.CTkRadioButton(
            frame, text="次数", variable=self.limit_var, value="count",
            command=self._on_limit_change,
        ).pack(side="left", padx=2)
        ctk.CTkRadioButton(
            frame, text="时长(s)", variable=self.limit_var, value="duration",
            command=self._on_limit_change,
        ).pack(side="left", padx=2)

        # ── 限制值 ──
        frame = ctk.CTkFrame(self.window)
        frame.pack(pady=5, padx=30, fill="x")
        ctk.CTkLabel(frame, text="限制值:").pack(side="left", padx=(10, 10))
        self.limit_entry = ctk.CTkEntry(frame, width=100)
        self.limit_entry.pack(side="left", padx=5)
        self.limit_entry.configure(state="disabled")

        # ── 状态 ──
        frame = ctk.CTkFrame(self.window)
        frame.pack(pady=10, padx=30, fill="x")
        self.status_dot = ctk.CTkLabel(
            frame, text="●", font=ctk.CTkFont(size=20), text_color="gray",
        )
        self.status_dot.pack(side="left", padx=(15, 3))
        self.status_label = ctk.CTkLabel(
            frame, text="已停止", font=ctk.CTkFont(size=14, weight="bold"),
            text_color="gray",
        )
        self.status_label.pack(side="left", padx=3)
        self.remaining_label = ctk.CTkLabel(frame, text="", text_color="gray")
        self.remaining_label.pack(side="right", padx=(0, 15))

        # ── 快捷键提示 ──
        frame = ctk.CTkFrame(self.window)
        frame.pack(pady=10, padx=30, fill="x")
        ctk.CTkLabel(
            frame, text="F6 开始    │    F7 停止",
            font=ctk.CTkFont(size=13),
        ).pack(pady=8)

    # ─────────────────── 模式 / 限制切换 ───────────────────

    def _on_mode_change(self):
        if self.mode_var.get() == "fixed":
            self._set_coord_state("normal")
        else:
            self._set_coord_state("disabled")

    def _on_limit_change(self):
        if self.limit_var.get() == "none":
            self.limit_entry.configure(state="disabled")
        else:
            self.limit_entry.configure(state="normal")

    def _on_speed_change(self, val):
        self.speed_label.configure(text=f"{int(float(val))} ms")

    def _set_coord_state(self, state):
        self.x_entry.configure(state=state)
        self.y_entry.configure(state=state)
        if state == "disabled":
            self.capture_btn.configure(state="disabled")
        else:
            self.capture_btn.configure(state="normal")

    # ─────────────────── 捕获鼠标位置 ───────────────────

    def _start_capture(self):
        if self.capturing:
            return
        self.capturing = True
        self._countdown = 3
        self._tick_capture()

    def _tick_capture(self):
        if self._countdown > 0:
            self.capture_btn.configure(text=f"{self._countdown} 秒后捕获...", state="disabled")
            self._countdown -= 1
            self.window.after(1000, self._tick_capture)
        else:
            pos = self.mouse_controller.position
            self.x_entry.delete(0, "end")
            self.x_entry.insert(0, str(int(pos[0])))
            self.y_entry.delete(0, "end")
            self.y_entry.insert(0, str(int(pos[1])))
            self.capture_btn.configure(text="捕获位置", state="normal")
            self.capturing = False

    # ─────────────────── 全局快捷键 ───────────────────

    def _start_hotkey_listener(self):
        self._kbd_listener = pynput_keyboard.Listener(on_press=self._on_key)
        self._kbd_listener.start()

    def _on_key(self, key):
        if key == pynput_keyboard.Key.f6:
            self.window.after(0, self.start)
        elif key == pynput_keyboard.Key.f7:
            self.window.after(0, self.stop)

    # ─────────────────── 启停 ───────────────────

    def start(self):
        if self.clicking:
            return
        if self.mode_var.get() == "fixed":
            try:
                int(self.x_entry.get())
                int(self.y_entry.get())
            except (ValueError, TypeError):
                self._flash_status("请先输入有效坐标", "orange")
                return

        self.clicking = True
        self.stop_event.clear()
        self._set_status("running")
        threading.Thread(target=self._click_loop, daemon=True).start()

    def stop(self):
        self.clicking = False
        self.stop_event.set()
        self._set_status("stopped")

    # ─────────────────── 点击循环 ───────────────────

    def _click_loop(self):
        mode = self.mode_var.get()
        button = BUTTON_MAP[self.button_var.get()]
        limit_type = self.limit_var.get()

        max_clicks = None
        max_seconds = None
        if limit_type == "count":
            try:
                max_clicks = int(self.limit_entry.get())
            except (ValueError, TypeError):
                max_clicks = None
        elif limit_type == "duration":
            try:
                max_seconds = float(self.limit_entry.get())
            except (ValueError, TypeError):
                max_seconds = None

        count = 0
        t_start = time.time()

        while not self.stop_event.is_set():
            time.sleep(self.speed_var.get() / 1000.0)
            if self.stop_event.is_set():
                break

            # 移动（固定坐标模式）
            if mode == "fixed":
                try:
                    x = int(self.x_entry.get())
                    y = int(self.y_entry.get())
                    self.mouse_controller.position = (x, y)
                except (ValueError, TypeError):
                    self.window.after(0, self.stop)
                    break

            self.mouse_controller.click(button, 1)
            count += 1

            # 更新计数
            self.window.after(0, lambda c=count: self.remaining_label.configure(text=f"已点击: {c}"))

            # 次数限制
            if max_clicks is not None and count >= max_clicks:
                self.window.after(0, self.stop)
                break

            # 时长限制
            if max_seconds is not None:
                elapsed = time.time() - t_start
                if elapsed >= max_seconds:
                    self.window.after(0, self.stop)
                    break
                remaining = max(0, max_seconds - elapsed)
                self.window.after(
                    0,
                    lambda r=remaining, c=count: self.remaining_label.configure(
                        text=f"剩余 {r:.1f}s | 已点 {c}"
                    ),
                )

    # ─────────────────── 状态更新 ───────────────────

    def _set_status(self, state):
        if state == "running":
            self.status_dot.configure(text_color="#4CAF50")
            self.status_label.configure(text="运行中", text_color="#4CAF50")
        else:
            self.status_dot.configure(text_color="gray")
            self.status_label.configure(text="已停止", text_color="gray")
            self.remaining_label.configure(text="")

    def _flash_status(self, msg, color):
        self.status_label.configure(text=msg, text_color=color)
        self.window.after(2000, lambda: self._set_status("stopped"))

    # ─────────────────── 启动 ───────────────────

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    MouseClicker().run()
