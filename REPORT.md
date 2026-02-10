# 画像 → STEP 変換: 忠実度向上のための手法検討

## 現状の問題

Claude Code に参考画像を見せて build123d の Python コードを生成させる「LLM 全任せ」方式では、以下の根本的な限界がある。

### 1. 寸法の推定精度が低い
- LLM は画像からピクセル単位の正確な比率を読み取れない
- 「クランクケース幅 44mm、角R 14mm」等はすべて推測値
- 微妙な比率の違いが全体の印象を大きく変える

### 2. 複雑な曲面の表現が困難
- 実機のクランクケースは有機的な曲面（compound curve）を持つ
- build123d のプリミティブ（Box, Cylinder, Extrude）では近似が粗い
- フィレット・ロフト等を駆使しても「CAD 臭さ」が抜けない

### 3. フィードバックループがない
- コード生成 → レンダリング → 目視比較 → 手動修正、の繰り返し
- 各イテレーションでの改善幅が小さく、収束が遅い

### 4. 暗黙知の欠落
- エンジン固有の設計慣習（ポート角度、フィン間隔のグラデーション等）
- 画像には写っていない裏側・内部構造の推測が必要

---

## 代替手法の比較

| 手法 | 忠実度 | 自動化度 | STEP出力 | 必要リソース |
|------|--------|----------|----------|-------------|
| A. AI Mesh生成 → BREP変換 | ★★★ | ★★★★ | △ (変換品質に依存) | GPU, TripoSR等 |
| B. フォトグラメトリ | ★★★★ | ★★★ | △ (後処理必要) | 多視点写真 |
| C. 反復リファインメント (CLIP誘導) | ★★★ | ★★★★ | ○ | CLIP model, GPU |
| D. シルエットベース再構成 | ★★★ | ★★★ | △ | 正面・側面・上面画像 |
| E. 既存CADテンプレート流用 | ★★★★★ | ★ | ◎ | 類似モデルのCADデータ |
| F. ハイブリッド (AI Mesh参照 + パラメトリックCAD) | ★★★★ | ★★★ | ◎ | GPU, LLM |
| 現状: LLM直接生成 | ★★ | ★★★★★ | ◎ | LLM のみ |

---

## 各手法の詳細

### A. AI 3D Mesh 生成 → BREP 変換

```
参考画像 → TripoSR / InstantMesh / Trellis → Mesh (OBJ/STL)
  → OpenCASCADE BRepBuilderAPI or FreeCAD → STEP
```

**利点:**
- 単一画像から3Dメッシュを直接生成できる
- 全体の形状・プロポーションは画像に忠実
- 処理が高速（数十秒〜数分）

**課題:**
- 出力はメッシュ（三角形の集合）であり、STEP（BREP曲面）ではない
- Mesh → STEP 変換は品質が安定しない（特に曲面のフィッティング）
- 細部（冷却フィンの薄板等）はメッシュ解像度に依存

**実装例:**
```python
# TripoSR で mesh 生成後、FreeCAD で STEP 変換
import subprocess
# 1. TripoSR でメッシュ生成
subprocess.run(["python", "triposr_infer.py", "--image", "reference.png", "--output", "mesh.obj"])
# 2. FreeCAD で STEP 変換
# FreeCAD のマクロ or Part.Shape.exportStep()
```

### B. フォトグラメトリ（多視点3D再構成）

```
多視点写真 (20-100枚) → COLMAP / Meshroom → 点群 → メッシュ
  → 表面再構成 → STEP変換
```

**利点:**
- 最も忠実な形状が得られる（実物があれば）
- テクスチャ情報も取得可能

**課題:**
- 実物のエンジンが手元に必要
- 多数の写真撮影が必要（20枚以上推奨）
- 参考画像が Web 検索結果の場合は使えない

### C. 反復リファインメント（CLIP 誘導最適化）

```
[ループ開始]
  LLM がコード生成 → レンダリング → CLIP で参考画像との類似度スコア計算
  → スコアと差分をフィードバック → LLM がコード修正
[スコアが閾値を超えるまで繰り返し]
```

**利点:**
- 現在のパイプライン（build123d + PyVista）をそのまま活用可能
- STEP 出力がネイティブに得られる
- 自動化可能

**課題:**
- CLIP の類似度は「意味的類似性」であり、幾何学的精度とは異なる
- 収束に多数のイテレーションが必要（コスト大）
- 局所最適に陥りやすい

**実装スケッチ:**
```python
import torch
import clip
from PIL import Image

def score_similarity(reference_path: str, rendered_path: str) -> float:
    """CLIP で参考画像とレンダリング画像の類似度を計算"""
    model, preprocess = clip.load("ViT-B/32")
    ref = preprocess(Image.open(reference_path)).unsqueeze(0)
    rendered = preprocess(Image.open(rendered_path)).unsqueeze(0)
    with torch.no_grad():
        ref_feat = model.encode_image(ref)
        ren_feat = model.encode_image(rendered)
        similarity = torch.cosine_similarity(ref_feat, ren_feat).item()
    return similarity

# メインループ
for iteration in range(max_iterations):
    generate_model()       # LLM がコード生成
    render_views()         # PyVista でレンダリング
    score = score_similarity("picture/ref.png", "out/model_isometric.png")
    if score > threshold:
        break
    feedback = f"類似度: {score:.3f}。以下の差分を修正してください: ..."
    # LLM に feedback を渡して再生成
```

### D. シルエットベース再構成（Visual Hull）

```
正面・側面・上面の3画像 → 各方向のシルエットマスク抽出
  → Visual Hull (シルエット交差) → ボクセル → メッシュ → STEP
```

**利点:**
- 3方向の画像があれば基本形状を再構成できる
- 今回のように正面・側面・上面のレンダリングが既にある場合に親和性が高い

**課題:**
- 凹形状（フィン間の溝等）の再現が困難
- 3方向では情報不足（斜めの形状が失われる）

### E. 既存 CAD テンプレート流用

```
類似エンジンの STEP/IGES を入手 → パラメータ修正 → 完成
```

**利点:**
- 最も高品質な結果が得られる
- 設計意図が保持される（パラメトリックなら寸法変更も容易）

**課題:**
- 類似モデルの CAD データが入手できるとは限らない
- ライセンスの問題
- パラメータ修正には CAD の知識が必要

### F. ハイブリッド: AI Mesh 参照 + パラメトリック CAD（推奨）

```
参考画像 → TripoSR → 参照メッシュ (寸法・比率の根拠)
  → LLM が参照メッシュの寸法を計測
  → build123d コード生成（メッシュ寸法に基づく正確なパラメータ）
  → STEP 出力
```

**利点:**
- AI メッシュから正確な寸法比率を抽出できる（画像からの推測より高精度）
- 最終出力はパラメトリック STEP（編集可能）
- LLM の強み（コード生成）と AI 3D の強み（形状認識）を組み合わせ

**課題:**
- パイプラインが複雑
- AI メッシュの品質が前提

**実装パイプライン:**
```python
import trimesh
import numpy as np

def extract_dimensions_from_mesh(mesh_path: str) -> dict:
    """AI生成メッシュから主要寸法を抽出"""
    mesh = trimesh.load(mesh_path)
    bounds = mesh.bounds
    dims = bounds[1] - bounds[0]

    # 各軸方向のスライスで断面形状を取得
    sections = {}
    for z in np.linspace(bounds[0][2], bounds[1][2], 20):
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section:
            sections[z] = {
                'bounds': section.bounds,
                'area': section.area,
            }

    return {
        'overall_length': dims[0],
        'overall_width': dims[1],
        'overall_height': dims[2],
        'cross_sections': sections,
    }

# 1. TripoSR でメッシュ生成
# 2. メッシュから寸法抽出
dims = extract_dimensions_from_mesh("ai_generated.obj")
# 3. 寸法情報を LLM に渡して build123d コード生成
```

---

## 推奨アプローチ

### 短期（現パイプライン改善）: 手法 C の簡易版

現在の build123d + PyVista パイプラインに**視覚フィードバックループ**を追加する。

1. `render.py` を拡張し、参考画像とレンダリング画像を並べた比較画像を生成
2. Claude Code が比較画像を見て差分を特定し、コードを修正
3. これを数回繰り返す（手動でも効果あり）

```
# render.py に追加する比較機能のイメージ
make compare-saito-fa-125-engine
# → out/saito-fa-125-engine/comparison.png (参考画像とレンダリングを並べた画像)
```

### 中期（精度向上）: 手法 F（ハイブリッド）

1. TripoSR 等で参照メッシュを生成するステップを追加
2. メッシュから自動寸法抽出するスクリプトを作成
3. 抽出した寸法を build123d コード生成のインプットとして使用

### 長期（完全自動化）: 手法 A + C の統合

1. AI 3D 生成でベースメッシュを取得
2. メッシュ → パラメトリック BREP 自動変換
3. CLIP 誘導の反復最適化で微調整
4. 最終的に編集可能な STEP を出力

---

## 結論

「LLM に画像を見せてCADコードを書かせる」現行方式は、**プロトタイピングの速度**では優れるが、**形状の忠実度**には本質的な限界がある。LLM は画像から正確な寸法比率を読み取れず、複雑な曲面を言語（コード）で記述するのも困難だからである。

忠実度を上げるには、**画像から幾何情報を抽出する別のステップ**（AI 3D 生成、フォトグラメトリ、シルエット抽出等）を挟み、その幾何情報を基にパラメトリック CAD を構築する**ハイブリッドパイプライン**が現実的な解となる。
