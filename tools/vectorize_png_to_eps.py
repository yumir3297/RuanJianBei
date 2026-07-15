from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def otsu_threshold(gray: np.ndarray) -> int:
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = gray.size
    sum_total = np.dot(np.arange(256), hist)

    sum_bg = 0.0
    weight_bg = 0.0
    best_var = -1.0
    threshold = 200

    for idx in range(256):
        weight_bg += hist[idx]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += idx * hist[idx]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if between > best_var:
            best_var = between
            threshold = idx
    return int(threshold)


def interpolate(p1: tuple[float, float], p2: tuple[float, float], v1: float, v2: float, level: float) -> tuple[float, float]:
    if abs(v2 - v1) < 1e-9:
        return ((p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5)
    t = (level - v1) / (v2 - v1)
    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))


def marching_squares(gray: np.ndarray, level: float) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    h, w = gray.shape
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []

    case_to_edges = {
        1: [("left", "top")],
        2: [("top", "right")],
        3: [("left", "right")],
        4: [("right", "bottom")],
        5: None,
        6: [("top", "bottom")],
        7: [("left", "bottom")],
        8: [("bottom", "left")],
        9: [("top", "bottom")],
        10: None,
        11: [("right", "bottom")],
        12: [("left", "right")],
        13: [("top", "right")],
        14: [("left", "top")],
    }

    for y in range(h - 1):
        for x in range(w - 1):
            tl = float(gray[y, x])
            tr = float(gray[y, x + 1])
            br = float(gray[y + 1, x + 1])
            bl = float(gray[y + 1, x])

            case = 0
            if tl < level:
                case |= 1
            if tr < level:
                case |= 2
            if br < level:
                case |= 4
            if bl < level:
                case |= 8

            if case in (0, 15):
                continue

            pts = {
                "top": interpolate((x, y), (x + 1, y), tl, tr, level),
                "right": interpolate((x + 1, y), (x + 1, y + 1), tr, br, level),
                "bottom": interpolate((x, y + 1), (x + 1, y + 1), bl, br, level),
                "left": interpolate((x, y), (x, y + 1), tl, bl, level),
            }

            if case in (5, 10):
                center = (tl + tr + br + bl) * 0.25
                if case == 5:
                    pairs = [("left", "top"), ("right", "bottom")] if center >= level else [("top", "right"), ("bottom", "left")]
                else:
                    pairs = [("top", "right"), ("bottom", "left")] if center >= level else [("left", "top"), ("right", "bottom")]
            else:
                pairs = case_to_edges[case]

            for edge_a, edge_b in pairs:
                segments.append((pts[edge_a], pts[edge_b]))

    return segments


def point_key(point: tuple[float, float], digits: int = 3) -> tuple[int, int]:
    scale = 10**digits
    return (int(round(point[0] * scale)), int(round(point[1] * scale)))


def build_loops(segments: list[tuple[tuple[float, float], tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    adjacency: dict[tuple[int, int], list[int]] = defaultdict(list)
    keyed_segments: list[tuple[tuple[int, int], tuple[int, int], tuple[float, float], tuple[float, float]]] = []

    for idx, (a, b) in enumerate(segments):
        ka = point_key(a)
        kb = point_key(b)
        keyed_segments.append((ka, kb, a, b))
        adjacency[ka].append(idx)
        adjacency[kb].append(idx)

    visited: set[int] = set()
    loops: list[list[tuple[float, float]]] = []

    for idx, (start_key, _, start_pt, _) in enumerate(keyed_segments):
        if idx in visited:
            continue

        loop = [start_pt]
        visited.add(idx)
        current_key = keyed_segments[idx][1]
        prev_seg = idx

        while True:
            current_pt = keyed_segments[prev_seg][3] if keyed_segments[prev_seg][1] == current_key else keyed_segments[prev_seg][2]
            loop.append(current_pt)
            if current_key == start_key:
                break

            next_seg = None
            for candidate in adjacency[current_key]:
                if candidate not in visited:
                    next_seg = candidate
                    break
            if next_seg is None:
                break

            visited.add(next_seg)
            ka, kb, a, b = keyed_segments[next_seg]
            current_key = kb if ka == current_key else ka
            prev_seg = next_seg

        if len(loop) > 3 and point_key(loop[0]) == point_key(loop[-1]):
            loops.append(loop[:-1])

    return loops


def perpendicular_distance(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    if start == end:
        return math.dist(point, start)
    x0, y0 = point
    x1, y1 = start
    x2, y2 = end
    num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
    den = math.hypot(y2 - y1, x2 - x1)
    return num / den


def rdp(points: list[tuple[float, float]], epsilon: float) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points[:]

    end = points[-1]
    start = points[0]
    max_dist = -1.0
    max_idx = -1

    for idx in range(1, len(points) - 1):
        dist = perpendicular_distance(points[idx], start, end)
        if dist > max_dist:
            max_dist = dist
            max_idx = idx

    if max_dist > epsilon:
        left = rdp(points[: max_idx + 1], epsilon)
        right = rdp(points[max_idx:], epsilon)
        return left[:-1] + right
    return [start, end]


def simplify_loop(loop: list[tuple[float, float]], epsilon: float) -> list[tuple[float, float]]:
    if len(loop) < 6:
        return loop
    reduced = rdp(loop + [loop[0]], epsilon)
    if len(reduced) > 1 and point_key(reduced[0]) == point_key(reduced[-1]):
        reduced = reduced[:-1]
    return reduced if len(reduced) >= 3 else loop


def write_eps(loops: list[list[tuple[float, float]]], width: int, height: int, output_path: Path) -> None:
    with output_path.open("w", encoding="ascii", newline="\n") as fh:
        fh.write("%!PS-Adobe-3.0 EPSF-3.0\n")
        fh.write(f"%%BoundingBox: 0 0 {width} {height}\n")
        fh.write("%%Creator: Codex vectorize_png_to_eps.py\n")
        fh.write("%%Pages: 1\n")
        fh.write("%%EndComments\n")
        fh.write("1 setlinejoin 1 setlinecap\n")
        fh.write("0 0 0 setrgbcolor\n")
        fh.write("newpath\n")

        for loop in loops:
            start_x, start_y = loop[0]
            fh.write(f"{start_x:.3f} {height - start_y:.3f} moveto\n")
            for x, y in loop[1:]:
                fh.write(f"{x:.3f} {height - y:.3f} lineto\n")
            fh.write("closepath\n")

        fh.write("eofill\n")
        fh.write("showpage\n")
        fh.write("%%EOF\n")


def vectorize_png_to_eps(input_path: Path, output_path: Path, simplify_epsilon: float = 0.9) -> None:
    image = Image.open(input_path).convert("L").filter(ImageFilter.GaussianBlur(radius=0.6))
    gray = np.asarray(image, dtype=np.uint8)
    threshold = max(140, min(235, otsu_threshold(gray) + 18))
    segments = marching_squares(gray, threshold)
    loops = build_loops(segments)
    loops = [simplify_loop(loop, simplify_epsilon) for loop in loops]
    loops = [loop for loop in loops if len(loop) >= 3]
    write_eps(loops, image.width, image.height, output_path)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python tools/vectorize_png_to_eps.py input.png output.eps [more pairs...]", file=sys.stderr)
        return 1
    if (len(argv) - 1) % 2 != 0:
        print("Input/output arguments must be provided in pairs.", file=sys.stderr)
        return 1

    args = argv[1:]
    for idx in range(0, len(args), 2):
        input_path = Path(args[idx])
        output_path = Path(args[idx + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        vectorize_png_to_eps(input_path, output_path)
        print(f"{input_path.name} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
