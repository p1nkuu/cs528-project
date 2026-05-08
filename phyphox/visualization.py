import matplotlib.pyplot as plt
plt.ion()
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.set_xlabel('X Axis', color='red')
ax.set_ylabel('Y Axis', color='green')
ax.set_zlabel('Z Axis', color='blue')
line_plot, = ax.plot([], [], [], marker='o', markersize=2)
pos_x, pos_y, pos_z = [], [], []

def plot_position_in_real_time(position):
    if position is None: return
    pos_x.append(position[0])
    pos_y.append(position[1])
    pos_z.append(position[2])
    
    line_plot.set_data(pos_x, pos_y)
    line_plot.set_3d_properties(pos_z)
    
    if len(pos_x) > 1:
        ax.set_xlim(min(pos_x) - 0.5, max(pos_x) + 0.5)
        ax.set_ylim(min(pos_y) - 0.5, max(pos_y) + 0.5)
        ax.set_zlim(min(pos_z) - 0.5, max(pos_z) + 0.5)
    
    plt.pause(0.01)