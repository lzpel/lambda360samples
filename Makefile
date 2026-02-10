MODELS = $(patsubst model/%.py,%,$(wildcard model/*.py))

.PHONY: all generate clean help

all: generate

# make generate-<model_name> で個別に実行
generate-%:
	uv run render.py $*

# 全てのモデルを生成
generate: $(foreach mod,$(MODELS),generate-$(mod))

clean:
	rm -rf out/
	rm -f *_temp.stl

help:
	@echo "CAD Rendering Makefile"
	@echo "Usage:"
	@echo "  make generate          - 全てのモデルを生成してレンダリング"
	@echo "  make generate-<name>   - 特定のモデル（model/<name>.py）を生成"
	@echo "  make clean             - 出力ディレクトリを削除"
