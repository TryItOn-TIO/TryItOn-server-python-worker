## Fitdit 코드 clone
``` bash
git clone https://github.com/BoyuanJiang/FitDiT.git
```

## Fitdit 모델 clone
```
# Git LFS 활성화 (시스템에 따라 최초 한 번만 실행)
sudo apt-get install git-lfs
git lfs install

# Hugging Face 저장소에서 모델 파일을 'local_model_dir' 폴더로 다운로드
git clone https://huggingface.co/BoyuanJiang/FitDiT models
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
