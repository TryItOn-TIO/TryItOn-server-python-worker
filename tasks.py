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
    """/generate 요청을 처리하고, 완료되면 Spring 서버에 콜백을 보냅니다."""
    
    tryOnImgUrl = task_args.get("tryOnImgUrl")
    userId = task_args.get("userId")
    spring_task_id = task_args.get("taskId")
    callback_url = task_args.get("callbackUrl")

    print(f"WORKER: /generate 작업 시작. Spring Task ID: {spring_task_id}")
    try:
        model_image = s3_handler.download_image_from_s3(tryOnImgUrl)
        pose_image, candidate, vton_img_det = vton_service.create_pose_data(model_image)
        upper_mask = vton_service.create_mask_only(model_image, vton_img_det, candidate, "Upper-body")
        lower_mask = vton_service.create_mask_only(model_image, vton_img_det, candidate, "Lower-body")

        base_key = f"users/{userId}/"
        
        pose_url = s3_handler.upload_pil_image_to_s3(pose_image, f"{base_key}pose.png")
        upper_mask_url = s3_handler.upload_pil_image_to_s3(upper_mask, f"{base_key}upper_mask.png")
        lower_mask_url = s3_handler.upload_pil_image_to_s3(lower_mask, f"{base_key}lower_mask.png")

        payload = {
            "taskId": spring_task_id,
            "status": "SUCCESS",
            "result": {
                "tryOnImgUrl": tryOnImgUrl,
                "poseImgUrl": pose_url,
                "upperMaskImgUrl": upper_mask_url,
                "lowerMaskImgUrl": lower_mask_url
            }
        }
    except Exception as e:
        print(f"WORKER ERROR (generate): {e}")
        payload = {"taskId": spring_task_id, "status": "FAILURE", "message": str(e)}

    finally:
        if callback_url:
            try:
                requests.post(callback_url, json=payload, timeout=10)
                print(f"WORKER: 콜백 전송 성공. URL: {callback_url}")
            except requests.RequestException as req_err:
                print(f"WORKER: 콜백 전송 실패. 에러: {req_err}")

    return payload


@celery_app.task(name="process_tryon_request")
def process_tryon_request(task_args: dict):
    """/tryon 요청을 처리하고, 완료되면 Spring 서버에 콜백을 보냅니다."""
    
    spring_task_id = task_args.get("taskId")
    callback_url = task_args.get("callbackUrl")
    userId = task_args.get("userId")
    garmentType = task_args.get("garmentType")
    # [수정] 오타 수정: tast_args -> task_args
    productId = task_args.get("productId") 

    print(f"WORKER: /tryon 작업 시작. Spring Task ID: {spring_task_id}")
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
        
        # [수정] S3 저장 경로 로직 반영
        result_key = f"cache/tryon/{userId}/{garmentType}-{productId}.png"
        result_url = s3_handler.upload_pil_image_to_s3(result_image, result_key)
        
        payload = {
            "taskId": spring_task_id,
            "status": "SUCCESS",
            "result": {"tryOnImgUrl": result_url}
        }
    except Exception as e:
        print(f"WORKER ERROR (tryon): {e}")
        payload = {"taskId": spring_task_id, "status": "FAILURE", "message": str(e)}

    finally:
        if callback_url:
            try:
                requests.post(callback_url, json=payload, timeout=10)
                print(f"WORKER: 콜백 전송 성공. URL: {callback_url}")
            except requests.RequestException as req_err:
                print(f"WORKER: 콜백 전송 실패. 에러: {req_err}")
                
    return payload