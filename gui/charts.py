import tkinter as tk
import math

class BarChart(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Configure>", self._on_resize)
        self._data = []
        self._color = "#1f6feb"
        self._frame_count = 0

    def draw(self, data: list[tuple[str, int]], color="#1f6feb"):
        """data = [(label, value), ...]"""
        self._data = data
        self._color = color
        self._frame_count = 0
        self._animate()

    def _on_resize(self, event):
        if self._data:
            self._render(min(self._frame_count, 30) / 30.0)

    def _animate(self):
        if self._frame_count <= 30:
            progress = self._frame_count / 30.0
            self._render(progress)
            self._frame_count += 1
            self.after(16, self._animate)

    def _render(self, progress=1.0):
        self.delete("all")
        if not self._data:
            return

        w = self.winfo_width()
        h = self.winfo_height()
        pad_x, pad_y = 40, 30

        # Draw grid
        max_val = max((val for _, val in self._data), default=1)
        if max_val == 0: max_val = 1
        
        for i in range(5):
            y = pad_y + (h - 2 * pad_y) * (1 - i / 4)
            self.create_line(pad_x, y, w - pad_x, y, fill="#30363d", dash=(2, 2))
            val_label = int(max_val * (i / 4))
            self.create_text(pad_x - 10, y, text=str(val_label), fill="gray", anchor="e", font=("Arial", 9))

        if len(self._data) == 0:
            return

        # Draw bars
        bar_width = min(40, (w - 2 * pad_x) / len(self._data) * 0.6)
        spacing = (w - 2 * pad_x) / len(self._data)

        for i, (label, val) in enumerate(self._data):
            x_center = pad_x + i * spacing + spacing / 2
            bar_h = (val / max_val) * (h - 2 * pad_y) * progress
            y_bottom = h - pad_y
            y_top = y_bottom - bar_h

            # Bar
            self.create_rectangle(x_center - bar_width/2, y_top, x_center + bar_width/2, y_bottom, fill=self._color, outline="")
            
            # Label
            if i % max(1, len(self._data)//7) == 0:  # Avoid crowding
                lbl = label.split("-")[-1] if "-" in label else label
                self.create_text(x_center, y_bottom + 10, text=lbl, fill="gray", font=("Arial", 9))

            # Value on top
            if val > 0 and progress > 0.8:
                self.create_text(x_center, y_top - 10, text=str(val), fill="white", font=("Arial", 9))


class DonutChart(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Configure>", self._on_resize)
        self._data = []

    def draw(self, data: list[tuple[str, int, str]]):
        """data = [(label, value, hex_color), ...]"""
        self._data = data
        self._render()

    def _on_resize(self, event):
        self._render()

    def _render(self):
        self.delete("all")
        if not self._data:
            return

        w = self.winfo_width()
        h = self.winfo_height()
        
        # Center coordinates for pie
        cx = w * 0.35
        cy = h / 2
        r = min(w, h) * 0.35
        
        total = sum(val for _, val, _ in self._data)
        if total == 0:
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#30363d", width=2)
            self.create_text(cx, cy, text="No Data", fill="gray")
            return

        start_ang = 90
        for label, val, color in self._data:
            extent = -(val / total) * 360
            if extent != 0:
                self.create_arc(cx - r, cy - r, cx + r, cy + r, 
                                start=start_ang, extent=extent, 
                                fill=color, outline=self["bg"], width=2)
            start_ang += extent

        # Inner hole for donut
        inner_r = r * 0.6
        self.create_oval(cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r, fill=self["bg"], outline="")

        # Legend
        leg_x = cx + r + 20
        leg_y_start = cy - (len(self._data) * 10)
        for i, (label, val, color) in enumerate(self._data):
            y = leg_y_start + i * 20
            self.create_rectangle(leg_x, y - 5, leg_x + 10, y + 5, fill=color, outline="")
            pct = int((val/total)*100)
            self.create_text(leg_x + 15, y, text=f"{label} ({pct}%)", fill="white", anchor="w", font=("Arial", 10))
