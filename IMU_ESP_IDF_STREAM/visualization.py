import random
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

directions = {
    "left": (-1, 0, 0),
    "right": (1, 0, 0),
    "up": (0, 1, 0),
    "down": (0, -1, 0),
    "forward": (0, 0, 1),
    "backward": (0, 0, -1)
}

# dummy model for now
def get_model_output():
    choices = ['Left', 'Right', 'Up', 'Down', 'Forward', 'Backward', 'Idle']
    return random.choice(choices)

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

x = [0]
y = [0]
z = [0]

line, = ax.plot([], [], [])

ax.set_xlim(-5, 5)
ax.set_ylim(-5, 5)
ax.set_zlim(-5, 5)

ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")

def update(frame):
    move = get_model_output()

    # if no move just return current line
    if move == "Idle":
        return line,

    # else get new direction
    dx, dy, dz = directions[move]

    x.append(x[-1] + dx)
    y.append(y[-1] + dy)
    z.append(z[-1] + dz)

    # update line
    line.set_data(x, y)
    line.set_3d_properties(z)

    return line,

ani = FuncAnimation(fig, update, interval=500)
plt.show()