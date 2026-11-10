"""Скрыпт для тэставання падключэння да Cloudflare R2 / S3 сховішча."""
import sys
from pathlib import Path

# Дадаем корань праекта ў sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.core.config import settings
from app.repositories.file_storage import FileStorage


def test_s3():
    print("=" * 60)
    print("Тэставанне падключэння да S3 / Cloudflare R2")
    print("=" * 60)
    print(f"STORAGE_BACKEND:   {settings.storage_backend}")
    print(f"S3_ENDPOINT_URL:   {settings.s3_endpoint_url}")
    print(f"S3_BUCKET_NAME:    {settings.s3_bucket_name}")
    print(f"S3_ACCESS_KEY_ID:  {'*' * 8 if settings.s3_access_key_id else 'НЕ ЗАДАДЗЕНЫ'}")
    print("-" * 60)

    if not settings.s3_endpoint_url or not settings.s3_bucket_name:
        print("[!] S3_ENDPOINT_URL або S3_BUCKET_NAME не сканфігураваныя ў .env.")
        print("    Каб выкарыстоўваць хмарнае сховішча, запоўніце параметры ў .env.")
        return False

    storage = FileStorage()
    client = storage.get_s3_client()
    if not client:
        print("[!] Не ўдалося ініцыялізаваць S3 кліент. Праверце наяўнасць бібліятэкі boto3.")
        return False

    test_key = "__test_connection__.txt"
    test_content = b"Clipmaker Free Tier R2 connection test."

    try:
        print(f"[*] Спроба загрузкі тэставага аб'екта '{test_key}' у бакет '{settings.s3_bucket_name}'...")
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=test_key,
            Body=test_content,
            ContentType="text/plain"
        )
        print("[+] Тэставы аб'ект паспяхова загружаны!")

        print("[*] Генерацыя Presigned URL для спампоўкі...")
        url = storage.get_presigned_url(test_key, expires_in=300)
        print(f"[+] Атрыманы Presigned URL:\n    {url}")

        print("[*] Выдаленне тэставага аб'екта з бакета...")
        client.delete_object(Bucket=settings.s3_bucket_name, Key=test_key)
        print("[+] Тэставы аб'ект паспяхова выдалены.")

        print("=" * 60)
        print("ВЫНІК: Падключэнне да Cloudflare R2 працуе бездакорна!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"[-] ПАМЫЛКА падключэння да S3: {e}")
        return False


if __name__ == "__main__":
    test_s3()
