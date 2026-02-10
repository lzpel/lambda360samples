import os
import sys
import importlib
import pyvista as pv
from build123d import export_stl, export_step

def render_model(model_name: str):
    # 1. モデルを動的にインポート
    try:
        module = importlib.import_module(f"model.{model_name}")
    except ImportError:
        print(f"Error: model/{model_name}.py が見つからへんわ。")
        sys.exit(1)
    
    if not hasattr(module, "generate"):
        print(f"Error: {model_name}.py に generate() 関数がないで。")
        sys.exit(1)
        
    # 2. モデル生成
    print(f"Generating model: {model_name}...")
    part = module.generate()
    
    # 3. レンダリング・エクスポート準備
    out_dir = os.path.join("out", model_name)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    # STEPファイルをエクスポート
    step_path = os.path.join(out_dir, "model.step")
    export_step(part, step_path)
    print(f"Exported: {step_path}")
    
    # レンダリング用の転送（STL経由）
    stl_path = f"{model_name}_temp.stl"
    export_stl(part, stl_path)
        
    print(f"Rendering to {out_dir}...")
    plotter = pv.Plotter(off_screen=True)
    mesh = pv.read(stl_path)
    plotter.add_mesh(mesh, color="lightblue", smooth_shading=True)
    
    views = [
        ("isometric", None),
        ("top", plotter.view_xy),
        ("front", plotter.view_xz),
        ("side", plotter.view_yz)
    ]
    
    for view_name, view_func in views:
        if view_name == "isometric":
            plotter.view_isometric()
        else:
            view_func()
            
        plotter.render()
        output_path = os.path.join(out_dir, f"{model_name}_{view_name}.png")
        plotter.screenshot(output_path)
        print(f"Saved: {output_path}")
        
    plotter.close()
    
    # 後片付け
    if os.path.exists(stl_path):
        os.remove(stl_path)
    print("Done!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run render.py <model_name>")
        sys.exit(1)
    
    render_model(sys.argv[1])
