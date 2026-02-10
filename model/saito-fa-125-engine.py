from build123d import *
import math


def generate() -> Part:
    """Saito FA-125 4ストローク グローエンジン - 画像に忠実なモデル"""

    # === 寸法パラメータ (mm) ===
    # 座標系: X=前後(+前=プロペラ側), Y=左右, Z=上下(+上=シリンダー側)
    # 原点: クランクケース中心

    # --- クランクケース ---
    cc_len = 55
    cc_wid = 44
    cc_hgt = 38
    cc_r = 14  # 大きめ角Rで実機のような丸みを再現

    cc_top = cc_hgt / 2
    cc_bot = -cc_hgt / 2
    cc_front = cc_len / 2
    cc_rear = -cc_len / 2

    # --- フロントベアリングハウジング ---
    fb_d = 36
    fb_len = 7

    # --- シリンダー ---
    cyl_od = 35
    cyl_base_z = cc_top - 4
    cyl_transition_d = 45
    cyl_transition_h = 5

    # --- 冷却フィン ---
    n_fins = 10
    fin_w = 54
    fin_d = 52
    fin_t = 1.0
    fin_gap = 3.0
    fin_r = 9
    fin_base_z = cyl_base_z + 8
    fin_top_z = fin_base_z + n_fins * (fin_t + fin_gap)

    # --- シリンダーヘッド ---
    hd_d = 48
    hd_w = 50
    hd_h = 16
    hd_r = 7
    hd_base_z = fin_top_z + 2
    hd_top_z = hd_base_z + hd_h

    # --- ロッカーアームカバー ---
    rc_len = 20
    rc_wid = 11
    rc_h = 8
    rc_sep = 26
    rc_r = 3

    # --- グロープラグ ---
    gp_d = 8
    gp_h = 8

    # --- プロペラハブ ---
    hub_d = 28
    hub_len = 16
    hub_flange_d = 42
    hub_flange_t = 4
    shaft_d = 8
    shaft_len = 12
    prop_washer_d = 34
    prop_washer_t = 2

    # --- 排気ポート ---
    exh_d = 12
    exh_len = 18
    exh_flange_w = 20
    exh_flange_h = 18
    exh_flange_t = 4
    exh_z = fin_base_z + 10

    # --- キャブレター ---
    carb_d = 14
    carb_len = 25
    carb_flange_w = 20
    carb_flange_h = 18
    carb_flange_t = 4
    carb_z = cc_top - 5
    carb_needle_d = 3
    carb_needle_len = 12

    # --- マウントレール ---
    mt_w = 9
    mt_l = cc_len + 14
    mt_t = 5
    mt_sep = cc_wid - 2
    mt_hole_d = 3.5

    # --- プッシュロッドチューブ (2本) ---
    pr_d = 6
    pr_cap_d = 9
    pr_cap_h = 3
    pr_positions = [(8, cyl_od / 2 + 2), (-6, cyl_od / 2 + 2)]

    # --- バックプレート ---
    bp_d = 38
    bp_t = 4
    bp_screw_r = 14
    bp_screw_d = 3

    with BuildPart() as engine:

        # =============================================
        # 1. クランクケース本体 (大きな角Rで丸みを出す)
        # =============================================
        with BuildSketch(Plane.XY.offset(cc_bot)) as sk_cc:
            Rectangle(cc_len, cc_wid)
            fillet(sk_cc.vertices(), radius=cc_r)
        extrude(amount=cc_hgt)

        # クランクケース → シリンダー 接合部 (広い円筒ベース)
        with BuildSketch(Plane.XY.offset(cc_top)):
            Circle(cyl_transition_d / 2)
        extrude(amount=cyl_transition_h)

        # =============================================
        # 2. フロントベアリングハウジング
        # =============================================
        with BuildSketch(Plane.YZ.offset(cc_front)):
            Circle(fb_d / 2)
        extrude(amount=fb_len)

        # =============================================
        # 3. シリンダー本体
        # =============================================
        with BuildSketch(Plane.XY.offset(cyl_base_z)):
            Circle(cyl_od / 2)
        extrude(amount=fin_top_z - cyl_base_z + 4)

        # =============================================
        # 4. 冷却フィン (10枚)
        # =============================================
        for i in range(n_fins):
            z = fin_base_z + i * (fin_t + fin_gap)
            with BuildSketch(Plane.XY.offset(z)) as sk_f:
                Rectangle(fin_d, fin_w)
                fillet(sk_f.vertices(), radius=fin_r)
            extrude(amount=fin_t)

        # =============================================
        # 5. シリンダーヘッド
        # =============================================
        with BuildSketch(Plane.XY.offset(hd_base_z)) as sk_hd:
            Rectangle(hd_d, hd_w)
            fillet(sk_hd.vertices(), radius=hd_r)
        extrude(amount=hd_h)

        # ヘッド冷却フィン (4枚)
        for i in range(4):
            z = hd_base_z + 2 + i * 3.5
            with BuildSketch(Plane.XY.offset(z)) as sk_hf:
                Rectangle(hd_d + 4, hd_w + 4)
                fillet(sk_hf.vertices(), radius=hd_r + 1)
            extrude(amount=1.0)

        # =============================================
        # 6. ロッカーアームカバー (2個、ドーム付き)
        # =============================================
        for y_off in [-rc_sep / 2, rc_sep / 2]:
            # 基部
            with BuildSketch(Plane.XY.offset(hd_top_z)) as sk_rc:
                with Locations([(0, y_off)]):
                    Rectangle(rc_len, rc_wid)
                    fillet(sk_rc.vertices(), radius=rc_r)
            extrude(amount=rc_h)
            # ドーム頂部
            with BuildSketch(Plane.XY.offset(hd_top_z + rc_h)):
                with Locations([(0, y_off)]):
                    Ellipse(rc_len / 2 - 2, rc_wid / 2 - 1)
            extrude(amount=2)

        # =============================================
        # 7. グロープラグ (六角ベース + 電極)
        # =============================================
        with BuildSketch(Plane.XY.offset(hd_top_z)):
            RegularPolygon(gp_d / 2, side_count=6)
        extrude(amount=gp_h)

        with BuildSketch(Plane.XY.offset(hd_top_z + gp_h)):
            Circle(gp_d / 2 - 1.5)
        extrude(amount=3)

        # =============================================
        # 8. プロペラハブ (フランジ + ワッシャー + 本体 + シャフト + ナット)
        # =============================================
        hub_start = cc_front + fb_len

        # ドライブフランジ
        with BuildSketch(Plane.YZ.offset(hub_start)):
            Circle(hub_flange_d / 2)
        extrude(amount=hub_flange_t)

        # プロペラワッシャー
        with BuildSketch(Plane.YZ.offset(hub_start + hub_flange_t)):
            Circle(prop_washer_d / 2)
        extrude(amount=prop_washer_t)

        # ハブ本体
        with BuildSketch(Plane.YZ.offset(hub_start)):
            Circle(hub_d / 2)
        extrude(amount=hub_len)

        # プロペラシャフト
        with BuildSketch(Plane.YZ.offset(hub_start + hub_len)):
            Circle(shaft_d / 2)
        extrude(amount=shaft_len)

        # プロペラナット (六角)
        with BuildSketch(Plane.YZ.offset(hub_start + hub_len + shaft_len - 6)):
            RegularPolygon(shaft_d / 2 + 2, side_count=6)
        extrude(amount=6)

        # =============================================
        # 9. 排気ポート (フランジ + スタブ + リップ)
        # =============================================
        # フランジ
        with BuildSketch(Plane.XZ.offset(cc_wid / 2)) as sk_ef:
            with Locations([(0, exh_z)]):
                Rectangle(exh_flange_w, exh_flange_h)
                fillet(sk_ef.vertices(), radius=3)
        extrude(amount=exh_flange_t)

        # 排気管スタブ
        with BuildSketch(Plane.XZ.offset(cc_wid / 2 + exh_flange_t)):
            with Locations([(0, exh_z)]):
                Circle(exh_d / 2)
        extrude(amount=exh_len - exh_flange_t)

        # 先端リップ
        with BuildSketch(Plane.XZ.offset(cc_wid / 2 + exh_len)):
            with Locations([(0, exh_z)]):
                Circle(exh_d / 2 + 1.5)
        extrude(amount=2)

        # =============================================
        # 10. キャブレター (フランジ + ベンチュリ + スロットルバレル
        #                   + ニードル + ノブ + スロットルアーム)
        # =============================================
        # インテークフランジ
        with BuildSketch(Plane.YZ.offset(cc_rear)) as sk_cf:
            with Locations([(0, carb_z)]):
                Rectangle(carb_flange_w, carb_flange_h)
                fillet(sk_cf.vertices(), radius=3)
        extrude(amount=-carb_flange_t)

        # ベンチュリ部 (細い)
        with BuildSketch(Plane.YZ.offset(cc_rear - carb_flange_t)):
            with Locations([(0, carb_z)]):
                Circle(carb_d / 2)
        extrude(amount=-10)

        # スロットルバレル (太い)
        with BuildSketch(Plane.YZ.offset(cc_rear - carb_flange_t - 10)):
            with Locations([(0, carb_z)]):
                Circle((carb_d + 4) / 2)
        extrude(amount=-(carb_len - carb_flange_t - 10))

        # ニードルバルブ
        with BuildSketch(Plane.YZ.offset(cc_rear - carb_len)):
            with Locations([(0, carb_z)]):
                Circle(carb_needle_d / 2)
        extrude(amount=-carb_needle_len)

        # ニードルノブ
        with BuildSketch(Plane.YZ.offset(cc_rear - carb_len - carb_needle_len)):
            with Locations([(0, carb_z)]):
                Circle(carb_needle_d + 1)
        extrude(amount=-3)

        # スロットルアーム
        throttle_x = cc_rear - carb_flange_t - 14
        with BuildSketch(Plane.XY.offset(carb_z + (carb_d + 4) / 2)):
            with Locations([(throttle_x, 0)]):
                Rectangle(4, 12)
        extrude(amount=3)

        # =============================================
        # 11. マウントレール (2本 + 4穴)
        # =============================================
        for y_off in [-mt_sep / 2, mt_sep / 2]:
            with BuildSketch(Plane.XY.offset(cc_bot - mt_t)) as sk_mt:
                with Locations([(0, y_off)]):
                    Rectangle(mt_l, mt_w)
                    fillet(sk_mt.vertices(), radius=1.5)
            extrude(amount=mt_t)

        # マウント穴
        for y_off in [-mt_sep / 2, mt_sep / 2]:
            for x_off in [-mt_l / 2 + 7, mt_l / 2 - 7]:
                with BuildSketch(Plane.XY.offset(cc_bot - mt_t - 0.1)):
                    with Locations([(x_off, y_off)]):
                        Circle(mt_hole_d / 2)
                extrude(amount=mt_t + 0.2, mode=Mode.SUBTRACT)

        # =============================================
        # 12. プッシュロッドチューブ (2本、端部キャップ付き)
        # =============================================
        pr_bottom_z = cc_top
        pr_top_z = hd_base_z + 4

        for px, py in pr_positions:
            # チューブ本体
            with BuildSketch(Plane.XY.offset(pr_bottom_z)):
                with Locations([(px, py)]):
                    Circle(pr_d / 2)
            extrude(amount=pr_top_z - pr_bottom_z)

            # 下部キャップ
            with BuildSketch(Plane.XY.offset(pr_bottom_z)):
                with Locations([(px, py)]):
                    Circle(pr_cap_d / 2)
            extrude(amount=pr_cap_h)

            # 上部キャップ
            with BuildSketch(Plane.XY.offset(pr_top_z - pr_cap_h)):
                with Locations([(px, py)]):
                    Circle(pr_cap_d / 2)
            extrude(amount=pr_cap_h)

        # =============================================
        # 13. バックプレート (円盤 + スクリュー4本)
        # =============================================
        with BuildSketch(Plane.YZ.offset(cc_rear)):
            Circle(bp_d / 2)
        extrude(amount=-bp_t)

        for angle_deg in [45, 135, 225, 315]:
            sy = bp_screw_r * math.cos(math.radians(angle_deg))
            sz = bp_screw_r * math.sin(math.radians(angle_deg))
            with BuildSketch(Plane.YZ.offset(cc_rear - bp_t)):
                with Locations([(sy, sz)]):
                    Circle(bp_screw_d / 2)
            extrude(amount=-2)

        # =============================================
        # 14. ブリーザーチューブ (クランクケース上面)
        # =============================================
        with BuildSketch(Plane.XY.offset(cc_top)):
            with Locations([(-cc_len / 4, -cc_wid / 2 + 6)]):
                Circle(2)
        extrude(amount=8)

    result = engine.part
    result.label = "Saito FA-125 Engine"
    return result


if __name__ == "__main__":
    from build123d import export_stl

    res = generate()
    export_stl(res, "saito_debug.stl")
