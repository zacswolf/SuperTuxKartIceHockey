# Source: https://github.com/pytorch/vision/blob/master/references/segmentation/transforms.py
import numpy as np
from PIL import Image
import random

import torch
from torchvision import transforms as T
from torchvision.transforms import functional as F


class RandomHorizontalFlip(object):
    def __init__(self, flip_prob=0.5):
        self.flip_prob = flip_prob

    def __call__(self, image, *args):
        if random.random() < self.flip_prob:
            image = F.hflip(image)
            args = tuple([(image.width-x, y) for x, y in boxes] for boxes in args)
        return (image,) + args


class Compose(object):
    def __init__(self, transforms):
        self.transforms = transforms

    def __call__(self, image, *args):
        for t in self.transforms:
            image, *args = t(image, *args)
        return (image,) + tuple(args)


class Normalize(T.Normalize):
    def __call__(self, image, *args):
        return (super().__call__(image),) + args


class ColorJitter(T.ColorJitter):
    def __call__(self, image, *args):
        return (super().__call__(image),) + args


class ToTensor(object):
    def __call__(self, image, *args):
        return (F.to_tensor(image),) + args


def _draw_detections(det, output_heat, radius=2):
    for d in det:
        # Compute the region to crop from the image
        cx, cy = d[0], d[1]
        R0, Rx, Ry = 2 * radius, 2 * radius + (int(cx) != cx), 2 * radius + (int(cy) != cy)
        # Crop
        heat_crop = output_heat[max(int(cy) - R0, 0):int(cy) + Ry + 1, max(int(cx) - R0, 0):int(cx) + Rx + 1]

        # Compute the Gaussian at the right position
        g_x = (-((torch.arange(heat_crop.size(1), device=heat_crop.device).float() - min(R0, int(cx)) - cx + int(
            cx)) / radius) ** 2).exp()
        g_y = (-((torch.arange(heat_crop.size(0), device=heat_crop.device).float() - min(R0, int(cy)) - cy + int(
            cy)) / radius) ** 2).exp()
        g = g_x[None, :] * g_y[:, None]

        # Update the heatmaps
        heat_crop[...] = torch.max(heat_crop, g)


def to_heatmap(im, *dets, device=None, **kwargs):
    det_map = torch.zeros((len(dets),) + im.shape[1:], device=device)
    for i, det in enumerate(dets):
        _draw_detections(det, det_map[i], **kwargs)
    return im, det_map


class ToHeatmap(object):
    def __init__(self, radius=2):
        self.radius = radius

    def __call__(self, image, *args):
        return to_heatmap(image, *args, radius=self.radius)
