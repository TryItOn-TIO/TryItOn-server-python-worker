# worker.py (수정 완료)

import requests
from celery import Celery
from celery.signals import worker_process_init
from datetime import datetime

# 설정 및 서비스 로직 임포트
from config import settings
# 프로젝트 구조에 맞게 s3_handler, vton_service 임포트
import s3_handler
import vton_service

# --- Celery 애플리케이션 생성 ---
celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    broker_connection_retry_on_startup=True
)

# --- 워커 프로세스 초기화 시 모델 로드 ---
@worker_process_init.connect
def init_model(**kwargs):
    print("==========================================")
    print("🚀 Celery Worker: Initializing Model...")
    vton_service.generator = vton_service.FitDiTGenerator(settings)
    print("✅ Celery Worker: Model Loaded Successfully!")
    print("==========================================")


# --- Celery 작업(Task) 정의 ---

@celery_app.task(name="process_generate_request")
def process_generate_request(task_args: dict):
    """/generate 요청을 처리하고, 결과를 Celery Backend에 저장합니다."""
    
    tryOnImgUrl = task_args.get("tryOnImgUrl")
    userId = task_args.get("userId")
    # spring_task_id와 callback_url은 더 이상 사용되지 않지만, 호환성을 위해 받아둘 수 있습니다.
    spring_task_id = task_args.get("taskId")

    print(f"WORKER: /generate 작업 시작. UserID: {userId}")
    try:
        model_image = s3_handler.download_image_from_s3(tryOnImgUrl)
        pose_image, candidate, vton_img_det = vton_service.create_pose_data(model_image)
        upper_mask = vton_service.create_mask_only(model_image, vton_img_det, candidate, "Upper-body")
        lower_mask = vton_service.create_mask_only(model_image, vton_img_det, candidate, "Lower-body")

        base_key = f"users/{userId}/"
        
        pose_url = s3_handler.upload_pil_image_to_s3(pose_image, f"{base_key}pose.png")
        upper_mask_url = s3_handler.upload_pil_image_to_s3(upper_mask, f"{base_key}upper_mask.png")
        lower_mask_url = s3_handler.upload_pil_image_to_s3(lower_mask, f"{base_key}lower_mask.png")

        # [수정] payload에서 불필요한 필드 제거, Celery 결과 포맷에 맞게 조정
        payload = {
            "tryOnImgUrl": tryOnImgUrl,
            "poseImgUrl": pose_url,
            "upperMaskImgUrl": upper_mask_url,
            "lowerMaskImgUrl": lower_mask_url
        }
        print(f"WORKER: /generate 작업 성공. UserID: {userId}")

    except Exception as e:
        print(f"WORKER ERROR (generate): {e}")
        # 실패 시 에러를 다시 발생시켜 Celery가 'FAILURE' 상태로 처리하도록 함
        raise e

    return payload


@celery_app.task(name="process_tryon_request")
def process_tryon_request(task_args: dict):
    """/tryon 요청을 처리하고, 결과를 Celery Backend에 저장합니다."""
    
    userId = task_args.get("userId")
    garmentType = task_args.get("garmentType")
    productId = task_args.get("productId") 
    cacheKey = task_args.get("cacheKey")

    print(f"WORKER: /tryon 작업 시작. UserID: {userId}, ProductID: {productId}")
    try:
        base_image = s3_handler.download_image_from_s3(task_args['baseImgUrl'])
        garment_image = s3_handler.download_image_from_s3(task_args['garmentImgUrl'])
        mask_image = s3_handler.download_image_from_s3(task_args['maskImgUrl'])
        pose_image = s3_handler.download_image_from_s3(task_args['poseImgUrl'])

        result_image = vton_service.perform_try_on(
            base_image=base_image,
            garment_image=garment_image,
            mask_image=mask_image,
            pose_image=pose_image
        )
        
        # result_key = f"cache/tryon/{userId}/{garmentType}-{productId}.png"
        result_key = cacheKey
        result_url = s3_handler.upload_pil_image_to_s3(result_image, result_key)
        
        # [수정] payload에서 불필요한 필드 제거, Celery 결과 포맷에 맞게 조정
        payload = {"tryOnImgUrl": result_url}
        print(f"WORKER: /tryon 작업 성공. UserID: {userId}, Result URL: {result_url}")

    except Exception as e:
        print(f"WORKER ERROR (tryon): {e}")
        # 실패 시 에러를 다시 발생시켜 Celery가 'FAILURE' 상태로 처리하도록 함
        raise e
                
    return payload