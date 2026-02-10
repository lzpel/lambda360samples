"""
フォトグラメトリ STL と build123d 生成モデルの比較ツール

Usage:
    uv run compare.py <model_name> <reference_stl>

Example:
    uv run compare.py saito-fa-125-engine scan/saito-fa-125-engine.stl

出力:
    out/<model_name>/compare_*.png    並列比較 (左:スキャン, 右:生成)
    out/<model_name>/overlay_*.png    半透明オーバーレイ (赤:スキャン, 青:生成)
    out/<model_name>/dimensions.txt   寸法差分レポート (Claude Code 向け)
"""

import os
import sys
import importlib
import numpy as np
import pyvista as pv
from build123d import export_stl, export_step


def load_reference(stl_path: str) -> pv.PolyData:
    """参照メッシュ(フォトグラメトリSTL)を読み込む"""
    return pv.read(stl_path)


def load_generated(model_name: str) -> tuple[pv.PolyData, str]:
    """build123dモデルを生成してメッシュ化"""
    module = importlib.import_module(f"model.{model_name}")
    part = module.generate()

    out_dir = os.path.join("out", model_name)
    os.makedirs(out_dir, exist_ok=True)

    step_path = os.path.join(out_dir, "model.step")
    export_step(part, step_path)
    print(f"Exported: {step_path}")

    stl_path = f"{model_name}_temp.stl"
    export_stl(part, stl_path)
    mesh = pv.read(stl_path)
    os.remove(stl_path)

    return mesh, out_dir


def align_meshes(reference: pv.PolyData, generated: pv.PolyData) -> pv.PolyData:
    """参照メッシュを生成モデルの座標系にアライメント (BBox中心+スケール)"""
    ref_center = np.array(reference.center)
    gen_center = np.array(generated.center)

    ref_bounds = np.array(reference.bounds).reshape(3, 2)
    gen_bounds = np.array(generated.bounds).reshape(3, 2)
    ref_size = np.max(ref_bounds[:, 1] - ref_bounds[:, 0])
    gen_size = np.max(gen_bounds[:, 1] - gen_bounds[:, 0])
    scale = gen_size / ref_size if ref_size > 0 else 1.0

    aligned = reference.copy()
    aligned.translate(-ref_center, inplace=True)
    aligned.scale(scale, inplace=True)
    aligned.translate(gen_center, inplace=True)

    return aligned


def extract_dimensions(mesh: pv.PolyData, name: str) -> dict:
    """メッシュから寸法情報を抽出 (Claude Code が改善に使うデータ)"""
    bounds = np.array(mesh.bounds).reshape(3, 2)
    dims = bounds[:, 1] - bounds[:, 0]

    # Z方向の断面解析
    z_min, z_max = bounds[2]
    n_slices = 20
    cross_sections = []
    for z in np.linspace(z_min + dims[2] * 0.05, z_max - dims[2] * 0.05, n_slices):
        try:
            sliced = mesh.slice(normal="z", origin=(0, 0, z))
            if sliced is not None and sliced.n_points > 0:
                sb = np.array(sliced.bounds).reshape(3, 2)
                cross_sections.append(
                    {
                        "z": float(z),
                        "width_x": float(sb[0, 1] - sb[0, 0]),
                        "width_y": float(sb[1, 1] - sb[1, 0]),
                    }
                )
        except Exception:
            pass

    vol = None
    try:
        vol = float(mesh.volume)
    except Exception:
        pass

    return {
        "name": name,
        "bounds": bounds,
        "dimensions": dims,
        "center": np.array(mesh.center),
        "volume": vol,
        "n_faces": mesh.n_cells,
        "cross_sections": cross_sections,
    }


def set_view(plotter, view_type: str):
    """ビューを設定"""
    if view_type == "isometric":
        plotter.view_isometric()
    elif view_type == "xy":
        plotter.view_xy()
    elif view_type == "xz":
        plotter.view_xz()
    elif view_type == "yz":
        plotter.view_yz()


def render_comparison(
    reference: pv.PolyData, generated: pv.PolyData, out_dir: str
):
    """並列レンダリングとオーバーレイレンダリング"""
    views = {
        "isometric": "isometric",
        "front": "xz",
        "side": "yz",
        "top": "xy",
    }

    for view_name, view_type in views.items():
        # --- 並列比較 (左右) ---
        pl = pv.Plotter(
            off_screen=True, shape=(1, 2), window_size=(1600, 800)
        )

        pl.subplot(0, 0)
        pl.add_mesh(reference, color="coral", smooth_shading=True)
        pl.add_text("Reference (Scan)", font_size=12)

        pl.subplot(0, 1)
        pl.add_mesh(generated, color="lightblue", smooth_shading=True)
        pl.add_text("Generated (STEP)", font_size=12)

        pl.link_views()
        for i in range(2):
            pl.subplot(0, i)
            set_view(pl, view_type)

        pl.render()
        path = os.path.join(out_dir, f"compare_{view_name}.png")
        pl.screenshot(path)
        pl.close()
        print(f"Saved: {path}")

        # --- オーバーレイ (半透明重ね合わせ) ---
        pl2 = pv.Plotter(off_screen=True, window_size=(800, 800))
        pl2.add_mesh(
            reference, color="coral", opacity=0.45, smooth_shading=True,
            label="Scan",
        )
        pl2.add_mesh(
            generated, color="lightblue", opacity=0.45, smooth_shading=True,
            label="STEP",
        )
        pl2.add_legend()
        set_view(pl2, view_type)
        pl2.render()
        path2 = os.path.join(out_dir, f"overlay_{view_name}.png")
        pl2.screenshot(path2)
        pl2.close()
        print(f"Saved: {path2}")


def write_dimension_report(ref_dims: dict, gen_dims: dict, out_dir: str):
    """寸法差分レポート (Claude Code がこのテキストを読んで改善する)"""
    lines = []
    lines.append("=" * 70)
    lines.append("寸法比較レポート — Claude Code 改善ループ用")
    lines.append("=" * 70)
    lines.append("")
    lines.append("このレポートの差分を参考に model/*.py のパラメータを修正してください。")
    lines.append("正の差分 = 生成モデルが大きすぎ、負の差分 = 小さすぎ。")
    lines.append("")

    # 全体寸法
    lines.append("--- 全体寸法 (mm) ---")
    lines.append(
        f"{'':20s} {'Reference':>12s} {'Generated':>12s} {'差分':>10s} {'比率':>8s}"
    )
    for i, axis in enumerate(["X (前後)", "Y (左右)", "Z (上下)"]):
        rd = ref_dims["dimensions"][i]
        gd = gen_dims["dimensions"][i]
        diff = gd - rd
        ratio = gd / rd if rd > 0 else 0
        lines.append(
            f"{axis:20s} {rd:12.2f} {gd:12.2f} {diff:+10.2f} {ratio:8.2%}"
        )

    # 体積
    rv = ref_dims["volume"]
    gv = gen_dims["volume"]
    if rv and gv:
        lines.append("")
        lines.append(
            f"{'体積 (mm³)':20s} {rv:12.1f} {gv:12.1f} {gv - rv:+10.1f} {gv / rv:8.2%}"
        )

    # 断面寸法
    lines.append("")
    lines.append("--- Z方向断面寸法 (各高さでのXY幅) ---")
    lines.append(
        f"{'Z位置':>8s}  {'Ref幅X':>8s} {'Gen幅X':>8s} {'差X':>7s}  "
        f"{'Ref幅Y':>8s} {'Gen幅Y':>8s} {'差Y':>7s}"
    )
    lines.append("-" * 70)

    ref_cs = ref_dims["cross_sections"]
    gen_cs = gen_dims["cross_sections"]

    for rc in ref_cs:
        closest = min(gen_cs, key=lambda g: abs(g["z"] - rc["z"]), default=None)
        if closest and abs(closest["z"] - rc["z"]) < 5:
            dx = closest["width_x"] - rc["width_x"]
            dy = closest["width_y"] - rc["width_y"]
            lines.append(
                f"{rc['z']:8.1f}  {rc['width_x']:8.2f} {closest['width_x']:8.2f} "
                f"{dx:+7.2f}  {rc['width_y']:8.2f} {closest['width_y']:8.2f} "
                f"{dy:+7.2f}"
            )

    # Claude Code 向けサマリー
    lines.append("")
    lines.append("--- 修正アクション候補 ---")

    dim_names = ["X (前後)", "Y (左右)", "Z (上下)"]
    for i in range(3):
        rd = ref_dims["dimensions"][i]
        gd = gen_dims["dimensions"][i]
        pct = (gd - rd) / rd * 100 if rd > 0 else 0
        if abs(pct) > 5:
            direction = "大きすぎ" if pct > 0 else "小さすぎ"
            lines.append(
                f"  * {dim_names[i]} が {abs(pct):.1f}% {direction} → 関連パラメータを調整"
            )

    report = "\n".join(lines)

    path = os.path.join(out_dir, "dimensions.txt")
    with open(path, "w") as f:
        f.write(report)

    print(report)
    print(f"\nSaved: {path}")


def main():
    if len(sys.argv) < 3:
        print("Usage: uv run compare.py <model_name> <reference_stl>")
        print(
            "Example: uv run compare.py saito-fa-125-engine scan/saito-fa-125-engine.stl"
        )
        sys.exit(1)

    model_name = sys.argv[1]
    ref_stl_path = sys.argv[2]

    if not os.path.exists(ref_stl_path):
        print(f"Error: {ref_stl_path} が見つからへん")
        sys.exit(1)

    # 1. 読み込み
    print(f"Loading reference: {ref_stl_path}")
    reference = load_reference(ref_stl_path)

    print(f"Generating model: {model_name}")
    generated, out_dir = load_generated(model_name)

    # 2. アライメント (BBox中心+スケール合わせ)
    print("Aligning meshes...")
    reference = align_meshes(reference, generated)

    # 3. 寸法抽出
    print("Extracting dimensions...")
    ref_dims = extract_dimensions(reference, "Reference (Scan)")
    gen_dims = extract_dimensions(generated, "Generated (STEP)")

    # 4. 比較レンダリング
    print("Rendering comparison...")
    render_comparison(reference, generated, out_dir)

    # 5. 寸法差分レポート
    print("")
    write_dimension_report(ref_dims, gen_dims, out_dir)

    print("\nDone!")


if __name__ == "__main__":
    main()
