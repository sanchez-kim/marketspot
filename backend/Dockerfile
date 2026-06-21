# MarketSpot 백엔드 (개발용). 코드는 compose 에서 볼륨 마운트하므로 이미지엔
# 의존성만 설치한다. editable(-e) 설치라 마운트된 /app 의 라이브 코드가 import 된다.
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 의존성 메타데이터 먼저 복사 → 코드만 바뀔 땐 레이어 캐시 유지.
COPY pyproject.toml ./
COPY app ./app
RUN pip install -e ".[data,dev]"

EXPOSE 8000

# --reload: 마운트된 코드 변경 시 자동 재기동(폴링은 compose 의 env 로 강제).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
