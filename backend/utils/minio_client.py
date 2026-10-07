import json
from minio import Minio
from minio.error import S3Error
from config import settings

_client: Minio | None = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_USER,
            secret_key=settings.MINIO_PASSWORD,
            secure=settings.MINIO_SECURE,
        )
        try:
            if not _client.bucket_exists(settings.MINIO_BUCKET):
                _client.make_bucket(settings.MINIO_BUCKET)
        except S3Error:
            pass
    return _client


def save_messages(user_id: int, conv_id: str, messages: list) -> None:
    client = get_client()
    data = json.dumps(messages, ensure_ascii=False).encode()
    from io import BytesIO
    client.put_object(
        settings.MINIO_BUCKET,
        f"{user_id}/{conv_id}.json",
        BytesIO(data),
        length=len(data),
        content_type="application/json",
    )


def load_messages(user_id: int, conv_id: str) -> list:
    # Dégradation propre : toute erreur MinIO (indispo, config, objet absent)
    # renvoie une liste vide plutôt que de faire planter la requête.
    try:
        client = get_client()
        resp = client.get_object(settings.MINIO_BUCKET, f"{user_id}/{conv_id}.json")
        return json.loads(resp.read())
    except Exception:
        return []


def delete_messages(user_id: int, conv_id: str) -> None:
    client = get_client()
    try:
        client.remove_object(settings.MINIO_BUCKET, f"{user_id}/{conv_id}.json")
    except S3Error:
        pass
