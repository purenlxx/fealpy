#!/usr/bin/env python3
# 

import argparse
import numpy as np
from fealpy.mesh import StructureQuadMesh
from fealpy.timeintegratoralg import UniformTimeLine 
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description=
        """
        在二维网格上用有限差分求解带 PML 层的 Maxwell 方程 
        """)

parser.add_argument('--NS',
        default=101, type=int,
        help='区域 x 和 y 方向的剖分段数（取奇数）， 默认为 101 段.')

parser.add_argument('--NP',
        default=20, type=int,
        help='PML 层的剖分段数（取偶数）， 默认为 20 段.')

parser.add_argument('--NT',
        default=500, type=int,
        help='时间剖分段数， 默认为 500 段.')

parser.add_argument('--ND',
        default=20, type=int,
        help='一个波长剖分的网格段数， 默认为 20 段.')

parser.add_argument('--R',
        default=0.5, type=int,
        help='网比， 默认为 0.5.')

parser.add_argument('--m',
        default=6, type=float,
        help='')

parser.add_argument('--sigma',
        default=100, type=float,
        help='最大电导率，默认取 100.')

args = parser.parse_args()

NS = args.NS
NP = args.NP
NT = args.NT
ND = args.ND
R = args.R
m = args.m
sigma = args.sigma

T0 = 0
T1 = NT
h = 1/NS
delta = h*NP
domain = [0, 1, 0, 1] # 原来的区域

def sigma_x(p):
    x = p[..., 0]
    shape = p.shape[:-1]
    val = np.zeros(shape, dtype=np.float64)
    flag = x < 0
    val[flag] = sigma*((0 - x[flag])/delta)**m
    flag = x > 1
    val[flag] = sigma*((x[flag] - 1)/delta)**m
    return val

def sigma_y(p):
    y = p[..., 1]
    shape = p.shape[:-1]
    val = np.zeros(shape, dtype=np.float64)
    flag = y < 0
    val[flag] = sigma*((0 - y[flag])/delta)**m
    flag = y > 1
    val[flag] = sigma*((y[flag] - 1)/delta)**m
    return val

domain = [0-delta, 1+delta, 0-delta, 1+delta] # 增加了 PML 层的区域
mesh = StructureQuadMesh(domain, nx=NS+2*NP, ny=NS+2*NP) # 建立结构网格对象
timeline = UniformTimeLine(T0, T1, NT)
dt = timeline.dt

sx0 = mesh.interpolation(sigma_x, intertype='cell')
sy0 = mesh.interpolation(sigma_y, intertype='cell') 

sx1 = mesh.interpolation(sigma_x, intertype='edgey')
sy1 = mesh.interpolation(sigma_y, intertype='edgey')

sx2 = mesh.interpolation(sigma_x, intertype='edgex')
sy2 = mesh.interpolation(sigma_y, intertype='edgex')

Bx0, By0 = mesh.function(etype='edge', dtype=np.float64)
Bx1, By1 = mesh.function(etype='edge', dtype=np.float64)
Hx, Hy = mesh.function(etype='edge', dtype=np.float64)
Dz0 = mesh.function(etype='cell', dtype=np.float64)
Dz1 = mesh.function(etype='cell', dtype=np.float64)
Ez = mesh.function(etype='cell', dtype=np.float64)

c1 = (2 - sy2[:, 1:-1] * R * h) / (2 + sy2[:, 1:-1] * R * h)
c2 = 2 * R / (2 + sy2[:, 1:-1] * R * h)

c3 = (2 - sx1[1:-1, :] * R * h) / (2 + sx1[1:-1, :] * R * h)
c4 = 2 * R / (2 + sx1[1:-1, :] * R * h)

c5 = (2 + sx2[:, 1:-1] * R * h) / 2
c6 = (2 - sx2[:, 1:-1] * R * h) / 2

c7 = (2 + sy1[1:-1, :] * R * h) / 2
c8 = (2 - sy1[1:-1, :] * R * h) / 2

c9 = (2 - sx0 * R * h) / (2 + sx0 * R * h)
c10 = 2 * R / (2 + sx0 * R * h)

c11 = (2 - sy0 * R * h) / (2 + sy0 * R * h)
c12 = 2 / (2 + sy0 * R * h)

i = (NS+2*NP)//2

def init(axes):
    data = axes.imshow(Ez, cmap='jet', vmin=-0.5, vmax=0.5, extent=domain)
    return data

def forward(n):
    global Ez
    t = T0 + n*dt
    if n == 0:
        return Ez, t
    else:
        Bx1[:, 1:-1] = c1 * Bx0[:, 1:-1] - c2 * (Ez[:, 1:] - Ez[:, 0:-1])

        By1[1:-1, :] = c3 * By0[1:-1, :] + c4 * (Ez[1:, :] - Ez[0:-1, :])

        Hx[:, 1:-1] += c5 * Bx1[:, 1:-1] - c6 * Bx0[:, 1:-1]
        Hy[1:-1, :] += c7 * By1[1:-1, :] - c8 * By0[1:-1, :]

        Dz1 = c9 * Dz0 + c10 * (Hy[1:, :] - Hy[0:-1, :] - Hx[:, 1:] + Hx[:, 0:-1])
        Ez *= c11
        Ez += c12 * (Dz1 - Dz0)

        Ez[i, i] = np.sin(2 * np.pi * n * (R / ND))

        Bx0[:] = Bx1
        By0[:] = By1
        Dz0[:] = Dz1

        return Ez, t

fig, axes = plt.subplots()
mesh.show_animation(fig, axes, domain, init, forward, frames=NT+1)
plt.show()
