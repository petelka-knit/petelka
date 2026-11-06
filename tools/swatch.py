"""Colour of a yarn skein from a shop photo (skein on a white background, label in the middle)."""
import numpy as np
from PIL import Image

def _lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)

def skein_colour(path):
    """Returns (hex, multi, share) or None. multi = the yarn shows two clearly different colours (melange, print)."""
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(float)
    h, w, _ = a.shape
    # background: near-white, taken from the border
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, 0)
    d = np.abs(a - bg).max(2)
    mask = d > 18
    if mask.mean() < 0.10:
        mask = d > 6
    if mask.mean() < 0.03:
        return None
    ys, xs = np.nonzero(mask)
    y0, y1 = np.percentile(ys, 2), np.percentile(ys, 98)
    x0, x1 = np.percentile(xs, 2), np.percentile(xs, 98)
    cy, cx, ry, rx = (y0 + y1) / 2, (x0 + x1) / 2, max(1, (y1 - y0) / 2), max(1, (x1 - x0) / 2)
    # the label sits in the middle of the skein: keep a ring near the edge of the ball (but not the very edge, which blends with the background)
    r = np.hypot((ys - cy) / ry, (xs - cx) / rx)
    ring = (r > 0.66) & (r < 0.93)
    px = a[ys[ring], xs[ring]]
    if len(px) < 60:
        px = a[ys, xs]
    lab = _lab(px)
    L = lab[:, 0]
    lo, hi = np.percentile(L, 40), np.percentile(L, 92)
    sel = (L >= lo) & (L <= hi)
    px, lab = px[sel], lab[sel]
    # two-colour test: 2-means in Lab
    c0, c1 = lab[np.argmin(lab[:, 0])], lab[np.argmax(lab[:, 0])]
    for _ in range(8):
        k = np.linalg.norm(lab - c0, axis=1) > np.linalg.norm(lab - c1, axis=1)
        if k.all() or (~k).all():
            break
        c0, c1 = lab[~k].mean(0), lab[k].mean(0)
    share = min(k.mean(), 1 - k.mean())
    dE = float(np.linalg.norm(c0 - c1))
    chroma_gap = abs(np.hypot(*c0[1:]) - np.hypot(*c1[1:]))
    hue_gap = np.linalg.norm(c0[1:] - c1[1:])
    multi = bool(share > 0.2 and dE > 30 and hue_gap > 18)
    rgb = np.median(px, 0)
    return '#%02x%02x%02x' % tuple(int(round(v)) for v in rgb), multi, round(float(share), 2)
