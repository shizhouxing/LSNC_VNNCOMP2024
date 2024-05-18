"""Generate benchmarking vnnlib files for trained models."""

import os
import shutil
import argparse
import csv
import random
import torch


tolerance = 1e-6
hole_size = 0.001

models = [
    {
        'name': 'quadrotor2d_state',
        'num_instances': 20,
        'timeout': 100,
        'box_limit': torch.tensor([0.75, 0.75, 1.57, 4, 4, 3]),
        'eps': 0.5,
        'value_levelset': 1.3392,
    },
    {
        'name': 'quadrotor2d_output',
        'num_instances': 20,
        'timeout': 200,
        'box_limit': torch.tensor([
            0.1,
            0.6283185307179586,
            0.2,
            0.6283185307179586,
            0.05,
            0.3141592653589793,
            0.1,
            0.3141592653589793
        ]),
        'eps': 0.3,
        'value_levelset': 0.045,
    }
]


def generate_instance(model, vnnlib_path):
    x_dim = model['box_limit'].shape[0]
    hole_dim = random.randint(0, x_dim - 1)
    box_lower = []
    box_upper = []
    for i in range(x_dim):
        if i == hole_dim:
            if random.randint(0, 1):
                lower = model['box_limit'][i] * hole_size
                upper = model['box_limit'][i]
            else:
                lower = -model['box_limit'][i]
                upper = -model['box_limit'][i] * hole_size
        else:
            lower = -model['box_limit'][i]
            upper = model['box_limit'][i]
        size = (upper - lower) * model['eps']
        sample = random.random()
        box_lower.append(lower + sample * (upper - lower - size))
        box_upper.append(box_lower[-1] + size)
    generate_vnnlib(model, box_lower, box_upper, vnnlib_path)


def generate_vnnlib(model, lower, upper, vnnlib_path):
    state_dim = len(lower)
    with open(vnnlib_path, 'w') as out:
        for i in range(state_dim):
            out.write(f"(declare-const X_{i} Real)\n")
        out.write("(declare-const Y_0 Real)\n")
        out.write("(declare-const Y_1 Real)\n")
        for i in range(2, 2 + state_dim):
            out.write(f"(declare-const Y_{i} Real)\n")
        out.write("\n")
        for i, (l, u) in enumerate(zip(lower, upper)):
            out.write(f"(assert (<= X_{i} {u}))\n")
            out.write(f"(assert (>= X_{i} {l}))\n\n")
        out.write(f"(assert (or\n")
        out.write(f"  (and (<= Y_0 -{tolerance}))\n")
        for i in range(state_dim):
            out.write(f"  (and (<= Y_{i+2} {-model['box_limit'][i] - tolerance}))\n")
            out.write(f"  (and (>= Y_{i+2} {model['box_limit'][i] + tolerance}))\n")
        out.write("))\n")
        levelset = model["value_levelset"]
        out.write(f'(assert (<= Y_1 {levelset}))\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('seed', type=int)
    args = parser.parse_args()

    random.seed(args.seed)

    if os.path.exists('vnnlib'):
        shutil.rmtree('vnnlib')
    os.makedirs('vnnlib')

    instances = []
    for model in models:
        onnx_path = f'onnx/{model["name"]}.onnx'
        for i in range(model['num_instances']):
            vnnlib_path = f'vnnlib/{model["name"]}_{i}.vnnlib'
            generate_instance(model, vnnlib_path)
            instances.append((onnx_path, vnnlib_path, model['timeout']))

    with open('instances.csv', 'w') as f:
        csv.writer(f).writerows(instances)
