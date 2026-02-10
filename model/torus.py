from build123d import *

def generate() -> Part:
    """トーラスのモデルを生成して返すで！"""
    with BuildPart() as torus_part:
        Torus(major_radius=10, minor_radius=3)
    return torus_part.part
