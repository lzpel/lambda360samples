from build123d import *

def generate() -> Part:
    """Saito FA-125 エンジンのモデルを生成するで！"""
    
    # --- パラメータ設定 ---
    crankcase_radius = 25
    crankcase_length = 60
    cylinder_radius = 18
    cylinder_height = 50
    fin_count = 12
    fin_thickness = 1.0
    fin_spacing = 3.0
    fin_outer_radius = 28
    prop_hub_radius = 12
    prop_hub_length = 20
    
    # --- 1. クランクケース (Main Body) ---
    with BuildPart() as crankcase:
        # メインの円筒体
        with BuildSketch(Plane.YZ) as s1:
            Circle(crankcase_radius)
        extrude(amount=crankcase_length)
        
        # エンジンマウント部分
        with BuildSketch(Plane.XY.offset(-crankcase_radius)) as s2:
            Rectangle(crankcase_length - 10, crankcase_radius * 2.5)
        extrude(amount=5)
        
    # --- 2. シリンダー (Cylinder & Fins) ---
    with BuildPart() as cylinder:
        # シリンダー本体
        with BuildSketch(Plane.XY.offset(crankcase_radius - 5)) as s3:
            Circle(cylinder_radius)
        extrude(amount=cylinder_height)
        
        # 冷却フィン
        for i in range(fin_count):
            with BuildSketch(Plane.XY.offset(crankcase_radius + 5 + i * fin_spacing)) as fs:
                # フィンの形状（少し角丸っぽく）
                Rectangle(fin_outer_radius * 2, fin_outer_radius * 2)
                fillet(fs.vertices(), radius=5)
            extrude(amount=fin_thickness)
            
    # --- 3. シリンダーヘッド & タペットカバー (Head & Valvetrain) ---
    with BuildPart() as head:
        head_height = crankcase_radius + cylinder_height + 5
        # ヘッド本体
        with BuildSketch(Plane.XY.offset(head_height)) as s4:
            Rectangle(cylinder_radius * 2.5, cylinder_radius * 2.5)
            fillet(s4.vertices(), radius=3)
        extrude(amount=15)
        
        # タペットカバー (2つの小さな隆起)
        for x_offset in [-10, 10]:
            with BuildSketch(Plane.XY.offset(head_height + 15)) as s5:
                with Locations((x_offset, 0)):
                    Rectangle(8, 15)
                    fillet(s5.vertices(), radius=2)
            extrude(amount=10)

    # --- 4. プロペラハブ (Propeller Hub) ---
    with BuildPart() as prop_hub:
        with BuildSketch(Plane.YZ.offset(crankcase_length)) as s6:
            Circle(prop_hub_radius)
        extrude(amount=prop_hub_length)
        
        # プロペラシャフト
        with BuildSketch(Plane.YZ.offset(crankcase_length + prop_hub_length)) as s7:
            Circle(5)
        extrude(amount=15)

    # --- 合体！ ---
    # パーツを適切に配置して結合する
    # 各コンポーネントをリストにして、Compoundとしてまとめるのが確実やな
    engine = Compound(label="Saito FA-125 Engine", children=[
        crankcase.part, 
        cylinder.part, 
        head.part, 
        prop_hub.part
    ])
    
    return engine

if __name__ == "__main__":
    # デバッグ用に単体で動かす場合はここ
    from build123d import export_stl
    res = generate()
    export_stl(res, "saito_debug.stl")
