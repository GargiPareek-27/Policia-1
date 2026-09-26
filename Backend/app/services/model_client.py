from pathlib import Path

import httpx

from app.core.config import settings


class ModelClient:
    """Calls the configured model service and stores its binary NPZ response."""

    async def predict(self, source_zip: str, result_path: str) -> str:
        headers = {"Authorization": f"Bearer {settings.model_api_key}"} if settings.model_api_key else {}
        timeout = httpx.Timeout(300.0, connect=10.0)
        async with httpx.AsyncClient(base_url=settings.model_api_url, timeout=timeout) as client:
            with Path(source_zip).open("rb") as archive:
                response = await client.post("/predict", files={"file": ("scan.zip", archive, "application/zip")}, headers=headers)
                response.raise_for_status()
        content = response.content
        if not content.startswith(b"PK\x03\x04"):
            raise ValueError("Model service did not return an NPZ file")
        target = Path(result_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return str(target)
