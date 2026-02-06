# Redactor - 日本語PII秘匿化システム

## 概要

日本語テキスト内の個人識別情報（PII）を検出し、`<ENTITY_TYPE1>`形式のトークンに置換する秘匿化システム。

## 技術スタック

- **検出エンジン**: Microsoft Presidio
- **NLPモデル**: spaCy `ja_core_news_lg`（日本語大規模モデル）
- **言語**: Python

## 検出対象エンティティ（16種類）

| カテゴリ | エンティティ | パターン例 |
|---------|------------|-----------|
| 個人情報 | `PERSON` | 漢字/かな/カナ/ローマ字の氏名 |
| 組織 | `ORG`, `ORGANIZATION` | 株式会社、有限会社等の接尾辞付き組織名 |
| 住所 | `LOCATION` | 都道府県＋市区町村＋番地 |
| 連絡先 | `PHONE_NUMBER` | `0XX-XXXX-XXXX`形式 |
| 連絡先 | `EMAIL_ADDRESS` | 標準メールアドレス形式 |
| 金融 | `CREDIT_CARD` | 14-16桁またはハイフン区切り |
| 金融 | `BANK_ACCOUNT` | 7桁の口座番号 |
| 金融 | `PIN` | 4桁の暗証番号 |
| 金融 | `SECURITY_CODE` | 3-4桁のセキュリティコード |
| 公的ID | `MY_NUMBER` | 12桁のマイナンバー |
| 公的ID | `DRIVERS_LICENSE` | 12桁の免許証番号 |
| 公的ID | `PASSPORT` | 英字1-2文字＋数字7-8桁 |
| 税務 | `TAX_NUMBER` | `T`＋13桁（インボイス番号） |
| 認証情報 | `PASSWORD` | `パスワード:`等の後に続く文字列 |
| 認証情報 | `SECRET_KEY` | `sk_`, `pk_`等のプレフィックス付きキー |
| 認証情報 | `CERTIFICATE` | `-----BEGIN ... -----END`ブロック |

## 検出ロジック

### 1. スコアリング

- **デフォルト閾値**: `0.85`（このスコア以上でPII認定）
- **コンテキスト強化**: 周辺に関連単語があるとスコア＋0.35
- **エンティティ別ベーススコア**: 0.55〜0.95（誤検知リスクに応じて設定）

### 2. コンテキスト単語（主要例）

```
PERSON: ["氏名", "名前", "名義", "担当", "様"]
PHONE_NUMBER: ["電話", "TEL", "連絡先", "携帯"]
CREDIT_CARD: ["カード番号", "クレジットカード", "決済"]
BANK_ACCOUNT: ["口座番号", "口座", "振込先", "銀行"]
PASSWORD: ["パスワード", "Password", "PW", "PASS"]
```

### 3. 誤検知フィルタリング

以下を除外して精度向上：
- 一般的な日本語単語（`情報`, `記録`, `設定`, `管理`等）
- ビジネス用語接尾辞（`〜記録`, `〜設定`, `〜管理`等）
- 数字のみのパターン（金額、年号）
- 改行を含む不正な検出範囲

### 4. 匿名化出力形式

```
元テキスト: 山田太郎 様の口座番号は 1234567 です
匿名化後:   <PERSON1> 様の口座番号は <BANK_ACCOUNT1> です
```

- 同一ファイル内で同じ値は同じインデックス番号を維持
- ファイルごとにインデックスはリセット

## ファイル構成

```
redactor/
├── redactor.py   # メインロジック（Analyzer設定、フィルタ、匿名化処理）
├── config.py     # 設定（閾値、パターン、除外リスト、コンテキスト単語）
└── evaluate.py   # 評価スクリプト（Precision/Recall/F1計測）
```

## 使用方法

```bash
# 基本実行
python -m redactor.redactor --input ./test_md --output ./redacted

# オプション
--prefix PREFIX  # 出力ファイル名にプレフィックス付与
--limit N        # 処理ファイル数を制限

# 評価実行
python -m redactor.evaluate --input ./test_md --limit 50
```

## 評価指標

- **Precision（適合率）**: 検出したPIIのうち正しいものの割合
- **Recall（再現率）**: 実際のPIIのうち検出できたものの割合
- **F1-Score**: PrecisionとRecallの調和平均

---

# 秘匿化APIサーバー仕様（FastAPI on Google Cloud）

> このセクションは「鉄壁AI（Teppeki AI Chat）」と連携する秘匿化APIサーバーの実装要件を定義します。

## 概要

本システムは上記のRedactorエンジンをFastAPIでラップし、Google Cloud Run上にホストします。鉄壁AI（Next.js）がHTTP経由でこのAPIを呼び出し、ユーザー入力の秘匿化およびLLM応答の復号化を行います。

### システム構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                        鉄壁AI (Next.js)                          │
│                     Vercel / Cloud Run                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              秘匿化API (FastAPI on Cloud Run)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ /anonymize   │  │ /deanonymize │  │ /health              │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │            Redactor Engine (Presidio + spaCy)           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         Session Store (Redis / Firestore)               │    │
│  │         マッピング情報の一時保存                           │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 技術スタック

| カテゴリ | 技術 | 備考 |
|---------|------|------|
| Webフレームワーク | FastAPI | 非同期対応、自動OpenAPIドキュメント |
| WSGIサーバー | Uvicorn | 本番環境ではGunicorn + Uvicorn workers |
| コンテナ | Docker | マルチステージビルド推奨 |
| ホスティング | Google Cloud Run | サーバーレス、自動スケーリング |
| セッションストア | Cloud Firestore or Memorystore (Redis) | マッピング情報の保存 |
| シークレット管理 | Secret Manager | APIキー等の機密情報 |
| CI/CD | Cloud Build | GitHub連携、自動デプロイ |
| コンテナレジストリ | Artifact Registry | Dockerイメージの保存 |
| ログ・監視 | Cloud Logging / Cloud Monitoring | 構造化ログ、アラート |

---

## APIエンドポイント仕様

### 1. POST `/anonymize` - 秘匿化

ユーザー入力テキストを秘匿化し、マッピング情報をセッションに保存します。

**Request:**
```json
{
  "text": "山田太郎様の電話番号は090-1234-5678です",
  "session_id": "chat_abc123"
}
```

**Response:**
```json
{
  "anonymized_text": "<PERSON1>様の電話番号は<PHONE_NUMBER1>です",
  "entities": [
    {
      "entity_type": "PERSON",
      "original_text": "山田太郎",
      "anonymized_token": "<PERSON1>",
      "start": 0,
      "end": 4,
      "score": 0.95
    },
    {
      "entity_type": "PHONE_NUMBER",
      "original_text": "090-1234-5678",
      "anonymized_token": "<PHONE_NUMBER1>",
      "start": 11,
      "end": 24,
      "score": 0.99
    }
  ]
}
```

### 2. POST `/deanonymize` - 復号化

秘匿化トークンを元のテキストに復元します。

**Request:**
```json
{
  "text": "<PERSON1>様へのご連絡は<PHONE_NUMBER1>までお願いします",
  "session_id": "chat_abc123"
}
```

**Response:**
```json
{
  "deanonymized_text": "山田太郎様へのご連絡は090-1234-5678までお願いします"
}
```

### 3. DELETE `/session/{session_id}` - セッション削除

チャット終了時にマッピング情報を削除します。

**Response:**
```json
{
  "message": "Session deleted successfully"
}
```

### 4. GET `/health` - ヘルスチェック

Cloud Runのヘルスチェック用エンドポイント。

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## ディレクトリ構成

```
.
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPIアプリケーション初期化
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── anonymize.py  # /anonymize エンドポイント
│   │   │   ├── deanonymize.py # /deanonymize エンドポイント
│   │   │   ├── session.py    # /session エンドポイント
│   │   │   └── health.py     # /health エンドポイント
│   │   └── deps.py           # 依存性注入（認証、DB接続等）
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # 環境変数・設定管理
│   │   └── security.py       # API認証ロジック
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py        # Pydanticスキーマ定義
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── redactor_service.py  # Redactorエンジンラッパー
│   │   └── session_service.py   # セッション管理（マッピング保存）
│   │
│   └── store/
│       ├── __init__.py
│       ├── base.py           # ストアの抽象基底クラス
│       ├── firestore.py      # Firestore実装
│       └── redis.py          # Redis実装（オプション）
│
├── redactor/                 # 既存のRedactorエンジン
│   ├── redactor.py
│   ├── config.py
│   └── evaluate.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # pytest fixtures
│   ├── test_anonymize.py
│   ├── test_deanonymize.py
│   └── test_session.py
│
├── Dockerfile
├── docker-compose.yml        # ローカル開発用
├── cloudbuild.yaml           # Cloud Build設定
├── requirements.txt
├── requirements-dev.txt      # 開発用依存関係
├── .env.example
└── README.md
```

---

## 実装パターン

### 1. FastAPIアプリケーション初期化（app/main.py）

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.routes import anonymize, deanonymize, session, health
from app.core.config import settings
from app.services.redactor_service import RedactorService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時: Redactorエンジンの初期化（spaCyモデル読み込み）
    app.state.redactor = RedactorService()
    yield
    # 終了時: リソース解放

app = FastAPI(
    title="Teppeki Redactor API",
    description="日本語PII秘匿化・復号化API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS設定（鉄壁AIからのリクエストを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(health.router, tags=["Health"])
app.include_router(anonymize.router, prefix="/anonymize", tags=["Anonymize"])
app.include_router(deanonymize.router, prefix="/deanonymize", tags=["Deanonymize"])
app.include_router(session.router, prefix="/session", tags=["Session"])
```

### 2. 設定管理（app/core/config.py）

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # アプリケーション設定
    PROJECT_NAME: str = "Teppeki Redactor API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # セキュリティ
    API_KEY: str  # 必須: 鉄壁AIからの認証用
    ALLOWED_ORIGINS: List[str] = ["https://teppeki-ai.vercel.app"]
    
    # セッションストア
    SESSION_STORE_TYPE: str = "firestore"  # "firestore" or "redis"
    SESSION_TTL_SECONDS: int = 86400  # 24時間
    
    # Firestore設定
    GCP_PROJECT_ID: str | None = None
    FIRESTORE_COLLECTION: str = "redactor_sessions"
    
    # Redis設定（オプション）
    REDIS_URL: str | None = None
    
    # Redactor設定
    DETECTION_THRESHOLD: float = 0.85
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 3. Pydanticスキーマ（app/models/schemas.py）

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class AnonymizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    session_id: str = Field(..., min_length=1, max_length=128)

class Entity(BaseModel):
    entity_type: str
    original_text: str
    anonymized_token: str
    start: int
    end: int
    score: float

class AnonymizeResponse(BaseModel):
    anonymized_text: str
    entities: List[Entity]

class DeanonymizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    session_id: str = Field(..., min_length=1, max_length=128)

class DeanonymizeResponse(BaseModel):
    deanonymized_text: str

class HealthResponse(BaseModel):
    status: str
    version: str
```

### 4. API認証（app/core/security.py）

```python
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required"
        )
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    return api_key
```

### 5. セッションストア（app/store/firestore.py）

```python
from google.cloud import firestore
from typing import Dict, Optional
from datetime import datetime, timedelta
from app.core.config import settings

class FirestoreSessionStore:
    def __init__(self):
        self.db = firestore.AsyncClient(project=settings.GCP_PROJECT_ID)
        self.collection = settings.FIRESTORE_COLLECTION
        self.ttl = settings.SESSION_TTL_SECONDS

    async def save_mapping(self, session_id: str, mapping: Dict[str, str]) -> None:
        """マッピング情報を保存（既存があればマージ）"""
        doc_ref = self.db.collection(self.collection).document(session_id)
        doc = await doc_ref.get()
        
        if doc.exists:
            existing = doc.to_dict().get("mapping", {})
            mapping = {**existing, **mapping}
        
        await doc_ref.set({
            "mapping": mapping,
            "updated_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(seconds=self.ttl)
        })

    async def get_mapping(self, session_id: str) -> Optional[Dict[str, str]]:
        """マッピング情報を取得"""
        doc_ref = self.db.collection(self.collection).document(session_id)
        doc = await doc_ref.get()
        
        if not doc.exists:
            return None
        
        return doc.to_dict().get("mapping", {})

    async def delete_session(self, session_id: str) -> bool:
        """セッションを削除"""
        doc_ref = self.db.collection(self.collection).document(session_id)
        await doc_ref.delete()
        return True
```

### 6. 秘匿化エンドポイント（app/api/routes/anonymize.py）

```python
from fastapi import APIRouter, Depends, Request
from app.models.schemas import AnonymizeRequest, AnonymizeResponse
from app.core.security import verify_api_key
from app.services.redactor_service import RedactorService
from app.services.session_service import SessionService

router = APIRouter()

@router.post("", response_model=AnonymizeResponse)
async def anonymize(
    request: Request,
    body: AnonymizeRequest,
    api_key: str = Depends(verify_api_key),
):
    redactor: RedactorService = request.app.state.redactor
    session_service = SessionService()
    
    # 秘匿化実行
    result = redactor.anonymize(body.text)
    
    # マッピング情報をセッションに保存
    mapping = {
        entity["anonymized_token"]: entity["original_text"]
        for entity in result["entities"]
    }
    await session_service.save_mapping(body.session_id, mapping)
    
    return AnonymizeResponse(
        anonymized_text=result["anonymized_text"],
        entities=result["entities"]
    )
```

---

## Dockerfile

```dockerfile
# ビルドステージ
FROM python:3.11-slim as builder

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# spaCyモデルのダウンロード
RUN python -m spacy download ja_core_news_lg

# 本番ステージ
FROM python:3.11-slim

WORKDIR /app

# 非rootユーザーの作成
RUN useradd --create-home appuser

# ビルドステージからの依存関係コピー
COPY --from=builder /root/.local /home/appuser/.local
COPY --from=builder /root/.cache /home/appuser/.cache

# アプリケーションコードのコピー
COPY --chown=appuser:appuser . .

# 環境変数設定
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Cloud Build設定（cloudbuild.yaml）

```yaml
steps:
  # Dockerイメージのビルド
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/${_SERVICE_NAME}:${SHORT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/${_SERVICE_NAME}:latest'
      - '.'

  # Artifact Registryへプッシュ
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/${_SERVICE_NAME}'

  # Cloud Runへデプロイ
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - '${_SERVICE_NAME}'
      - '--image'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/${_SERVICE_NAME}:${SHORT_SHA}'
      - '--region'
      - '${_REGION}'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--memory'
      - '2Gi'
      - '--cpu'
      - '2'
      - '--min-instances'
      - '0'
      - '--max-instances'
      - '10'
      - '--set-secrets'
      - 'API_KEY=redactor-api-key:latest'

substitutions:
  _REGION: asia-northeast1
  _REPOSITORY: teppeki-redactor
  _SERVICE_NAME: redactor-api

options:
  logging: CLOUD_LOGGING_ONLY
```

---

## 環境変数一覧

### 本番環境（Cloud Run）

| 変数名 | 説明 | 設定方法 |
|--------|------|----------|
| `API_KEY` | 鉄壁AIからの認証キー | Secret Manager |
| `GCP_PROJECT_ID` | GCPプロジェクトID | 自動設定 |
| `SESSION_STORE_TYPE` | `firestore` | 環境変数 |
| `FIRESTORE_COLLECTION` | `redactor_sessions` | 環境変数 |
| `ALLOWED_ORIGINS` | `https://teppeki-ai.vercel.app` | 環境変数 |
| `DETECTION_THRESHOLD` | `0.85` | 環境変数 |

### ローカル開発（.env）

```env
# アプリケーション
DEBUG=true
API_KEY=dev-api-key-12345

# セッションストア
SESSION_STORE_TYPE=firestore
GCP_PROJECT_ID=your-project-id
FIRESTORE_COLLECTION=redactor_sessions_dev
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json

# CORS
ALLOWED_ORIGINS=["http://localhost:3000"]

# Redactor
DETECTION_THRESHOLD=0.85
```

---

## 鉄壁AI（Next.js）側のクライアント実装例

鉄壁AIのコードベースに実装する秘匿化APIクライアント:

```typescript
// lib/presidio/client.ts
const PRESIDIO_API_URL = process.env.PRESIDIO_API_URL!;
const PRESIDIO_API_KEY = process.env.PRESIDIO_API_KEY!;

interface Entity {
  entity_type: string;
  original_text: string;
  anonymized_token: string;
  start: number;
  end: number;
  score: number;
}

interface AnonymizeResponse {
  anonymized_text: string;
  entities: Entity[];
}

interface DeanonymizeResponse {
  deanonymized_text: string;
}

export async function anonymize(
  text: string,
  sessionId: string
): Promise<AnonymizeResponse> {
  const res = await fetch(`${PRESIDIO_API_URL}/anonymize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': PRESIDIO_API_KEY,
    },
    body: JSON.stringify({ text, session_id: sessionId }),
  });

  if (!res.ok) {
    throw new Error(`Anonymize failed: ${res.status}`);
  }

  return res.json();
}

export async function deanonymize(
  text: string,
  sessionId: string
): Promise<DeanonymizeResponse> {
  const res = await fetch(`${PRESIDIO_API_URL}/deanonymize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': PRESIDIO_API_KEY,
    },
    body: JSON.stringify({ text, session_id: sessionId }),
  });

  if (!res.ok) {
    throw new Error(`Deanonymize failed: ${res.status}`);
  }

  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${PRESIDIO_API_URL}/session/${sessionId}`, {
    method: 'DELETE',
    headers: {
      'X-API-Key': PRESIDIO_API_KEY,
    },
  });
}
```

---

## セキュリティ要件

1. **API認証**: `X-API-Key`ヘッダーによる認証必須
2. **HTTPS強制**: Cloud RunはデフォルトでマネージドSSL
3. **CORS制限**: 鉄壁AIのドメインのみ許可
4. **Secret Manager**: APIキー等の機密情報は環境変数に直接書かない
5. **セッションTTL**: マッピング情報は24時間で自動削除
6. **入力バリデーション**: テキスト長の上限チェック（50,000文字）

---

## モニタリング・ログ

### 構造化ログ

```python
import structlog

logger = structlog.get_logger()

# リクエストログ
logger.info(
    "anonymize_request",
    session_id=session_id,
    text_length=len(text),
    entities_count=len(entities),
)
```

### Cloud Monitoringアラート

| メトリクス | 閾値 | アクション |
|-----------|------|-----------|
| レイテンシ（p99） | > 5秒 | Slackアラート |
| エラー率 | > 1% | Slackアラート |
| インスタンス数 | > 8 | メール通知 |

---

## デプロイ手順

### 初回セットアップ

```bash
# 1. GCPプロジェクト設定
gcloud config set project YOUR_PROJECT_ID

# 2. 必要なAPIを有効化
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com

# 3. Artifact Registryリポジトリ作成
gcloud artifacts repositories create teppeki-redactor \
  --repository-format=docker \
  --location=asia-northeast1

# 4. Secret Managerにシークレット登録
echo -n "your-api-key" | gcloud secrets create redactor-api-key \
  --data-file=-

# 5. Cloud Buildトリガー作成（GitHub連携）
gcloud builds triggers create github \
  --repo-name=teppeki-redactor \
  --repo-owner=your-org \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml
```

### 手動デプロイ

```bash
# ローカルからビルド＆デプロイ
gcloud builds submit --config=cloudbuild.yaml
```

---

## ローカル開発

```bash
# 依存関係インストール
pip install -r requirements.txt
pip install -r requirements-dev.txt

# spaCyモデルダウンロード
python -m spacy download ja_core_news_lg

# 開発サーバー起動
uvicorn app.main:app --reload --port 8000

# テスト実行
pytest -v

# Firestore エミュレータ起動（オプション）
gcloud emulators firestore start --host-port=localhost:8081
```

---


