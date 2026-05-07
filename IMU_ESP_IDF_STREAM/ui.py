import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import random

GESTURES = ["left", "right", "up", "down", "forward", "backward"]
PASSWORD = ["left", "up", "right", "down", "forward", "backward"]

DIRECTION_MAP = {
    "left": (-1, 0, 0),
    "right": (1, 0, 0),
    "up": (0, 0, 1),
    "down": (0, 0, -1),
    "forward": (0, 1, 0),
    "backward": (0, -1, 0)
}

STEP_SIZE = 1

class GestureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gesture UI + 3D Visualization")

        self.current_input = []
        self.current_pos = np.array([0.0, 0.0, 0.0])
        self.points = [self.current_pos.copy()]
        self.last_gesture = None

        self.canvas = tk.Canvas(root, width=600, height=80)
        self.canvas.pack()

        self.rects = []
        self.draw_segments()

        self.fig = plt.figure(figsize=(5, 4))
        self.ax = self.fig.add_subplot(111, projection='3d')

        self.line, = self.ax.plot([], [], [])

        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)
        self.ax.set_zlim(0, 10)

        self.canvas3d = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas3d.get_tk_widget().pack()

        tk.Button(root, text="make gesture", command=self.add_prediction).pack()

    def draw_segments(self):
        width = 600 // len(PASSWORD)
        for i in range(len(PASSWORD)):
            rect = self.canvas.create_rectangle(
                i * width, 0, (i + 1) * width, 80,
                fill="lightgray"
            )
            self.rects.append(rect)

    def update_segments(self):
        for i, rect in enumerate(self.rects):
            if i < len(self.current_input):
                self.canvas.itemconfig(rect, fill="green")
            else:
                self.canvas.itemconfig(rect, fill="lightgray")

    def add_segment(self, direction, steps=10):
        direction = np.array(direction)
        step_vec = direction * STEP_SIZE / steps

        for _ in range(steps):
            self.current_pos = self.current_pos + step_vec
            self.points.append(self.current_pos.copy())

    def update_3d_plot(self):
        xs, ys, zs = zip(*self.points)

        self.line.set_data(xs, ys)
        self.line.set_3d_properties(zs)

        self.ax.set_xlim(min(xs)-1, max(xs)+1)
        self.ax.set_ylim(min(ys)-1, max(ys)+1)
        self.ax.set_zlim(min(zs)-1, max(zs)+1)

        self.canvas3d.draw()

    def add_prediction(self, gesture=None):
        # replace w/ model output
        if gesture is None:
            gesture = random.choice(GESTURES)

        print("Predicted:", gesture)

        if gesture == self.last_gesture:
            # smaller movement if holding same gesture
            self.add_segment(DIRECTION_MAP[gesture], steps=3)
        else:
            self.add_segment(DIRECTION_MAP[gesture], steps=10)
            self.current_input.append(gesture)
            self.update_segments()
            self.last_gesture = gesture

        self.update_3d_plot()

        if len(self.current_input) == len(PASSWORD):
            self.check_password()

    def check_password(self):
        if self.current_input == PASSWORD:
            messagebox.showinfo("Correct!")
        else:
            messagebox.showerror("Incorrect")
        self.reset()

    def reset(self):
        self.current_input = []
        self.current_pos = np.array([0.0, 0.0, 0.0])
        self.points = [self.current_pos.copy()]
        self.last_gesture = None

        self.update_segments()
        self.update_3d_plot()

root = tk.Tk()
app = GestureApp(root)
root.mainloop()