## Fitdit 코드 clone
``` bash
git clone https://github.com/BoyuanJiang/FitDiT.git
```

## Fitdit 모델 clone
```
# 1. 모델들을 담을 부모 폴더 생성
mkdir -p models

# 2. Git-LFS 활성화
git lfs install

# 3. FitDiT 메인 모델 다운로드
git clone https://huggingface.co/BoyuanJiang/FitDiT models/FitDiT

# 4. CLIP-L 모델 다운로드
git clone https://huggingface.co/openai/clip-vit-large-patch14 models/clip-vit-large-patch14

# 5. CLIP-bigG 모델 다운로드
git clone https://huggingface.co/laion/CLIP-ViT-bigG-14-laion2B-39B-b160k models/CLIP-ViT-bigG-14-laion2B-39B-b160k
```

## docker 빌드
``` bash
docker run --gpus all --rm -it \
  --name my-gpu-worker-debug \
  -v "$(pwd)/FitDiT:/app" \
  -v "$(pwd)/models:/models" \
  --entrypoint /bin/bash \
  fitdit-worker
  ```

  ## Server 실행
  ``` bash
  celery -A tasks.celery_app worker --loglevel=info --concurrency=1
  ```
