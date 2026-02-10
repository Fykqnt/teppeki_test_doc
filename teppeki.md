# 鉄壁AIチャット - プロジェクト仕様書

> このドキュメントはAI駆動開発のためのコンテキストファイルです。実装時は必ずこの仕様に従ってください。

## プロジェクト概要

**鉄壁AIチャット**は、ChatGPTライクなUIで、ユーザーが意識することなくPII（個人情報）の秘匿化処理が自動で行われるプライバシーファーストのチャットアプリケーションです。

### コアコンセプト

- ユーザーの入力は**Presidio API（Pythonの別サーバー）で秘匿化**されてからLLMに送信される
- LLMの応答は**Presidioで復号化**されてからユーザーに表示される
- **LLMプロバイダーには生のPIIが一切渡らない**設計

---

## 技術スタック

| カテゴリ | 技術 | 備考 |
|---------|------|------|
| フレームワーク | Next.js 16 | App Router使用 |
| 言語 | TypeScript | 厳格な型付け |
| UIコンポーネント | shadcn/ui | Radix UIベース |
| スタイリング | Tailwind CSS | v4 |
| 認証 | Supabase Auth | メール/Google OAuth |
| データベース | Supabase | PostgreSQL |
| AI/LLM | Vercel AI SDK | @ai-sdk/google, @ai-sdk/openai |
| LLMモデル | Gemini 3 Flash Preview, GPT-5.2 | マルチモーダル対応 |
| 秘匿化 | Python API(別サーバー) |
| ファイル処理 | pdf-parse, xlsx | PDF・Excel解析 |
| アナリティクス | Vercel Analytics | - |
| パッケージ管理 | pnpm | - |

---

## アーキテクチャ

### データフロー（重要）

```
[ユーザー入力（テキスト/画像/PDF/Excel）]
     │
     ▼
[Next.js API Route: /api/chat]
     │
     ├─── 認証チェック（Supabase Auth）
     │
     ├─── 使用量チェック（lib/supabase/usage.ts）
     │
     ├─── 入力バリデーション（lib/input-validation.ts）
     │    ├─ プロンプトインジェクション検出
     │    └─ サニタイズ処理
     │
     ├─── ファイル処理（マルチモーダル対応）
     │    ├─ 画像: Base64で直接LLMへ
     │    ├─ PDF: pdf-parseでテキスト抽出
     │    └─ Excel: xlsxでテキスト抽出
     │
     ▼
[LLM Provider (Google Gemini / OpenAI)]
     │ ストリーミング応答
     │ 使用トークン数を記録
     ▼
[ユーザーに表示]
```

### 秘匿化の仕組み（lib/pii.ts）

| 元テキスト | 秘匿化後 | PIIタイプ |
|-----------|---------|-----------|
| 山田太郎 | `[NAME_REDACTED]` | 人名 |
| tanaka@example.com | `[EMAIL_REDACTED]` | メールアドレス |
| 090-1234-5678 | `[PHONE_REDACTED]` | 電話番号 |
| 東京都渋谷区... | `[ADDRESS_REDACTED]` | 住所 |
| 1234-5678-9012-3456 | `[CARD_REDACTED]` | クレジットカード |

### サポートモデル

| モデルID | プロバイダー | 特徴 |
|----------|-------------|------|
| `gemini-3-flash-preview` | Google | デフォルト、高速、マルチモーダル |
| `gpt-5.2` | OpenAI | 高精度 |

---

## ディレクトリ構成と責務

```
.
├── app/                          # Next.js App Router
│   ├── api/
│   │   └── chat/route.ts         # POST: LLMストリーミング + マルチモーダル対応
│   │
│   ├── auth/                     # 認証関連ルート
│   │   ├── callback/route.ts     # OAuth コールバック（Google認証）
│   │   └── confirm/route.ts      # メールOTP検証
│   │
│   ├── login/page.tsx            # ログインページ（メール/Google）
│   ├── signup/page.tsx           # サインアップページ
│   │
│   ├── page.tsx                  # メインチャット画面
│   ├── layout.tsx                # ルートレイアウト（メタデータ、Analytics）
│   └── globals.css
│
├── components/                   # コンポーネント（フラット構造）
│   ├── app-provider.tsx          # アプリ全体のプロバイダー統合
│   ├── auth-provider.tsx         # 認証状態管理プロバイダー
│   ├── auth-button.tsx           # ログイン/ログアウトボタン
│   ├── auth-dialog.tsx           # 認証ダイアログ
│   ├── theme-provider.tsx        # ダークモード等テーマ管理
│   │
│   ├── chat-header.tsx           # チャットヘッダー
│   ├── chat-main.tsx             # メインチャットエリア
│   ├── composer.tsx              # メッセージ入力欄（ファイル添付対応）
│   ├── message-item.tsx          # 個別メッセージ表示
│   ├── message-list.tsx          # メッセージ一覧
│   ├── sidebar.tsx               # サイドバー
│   │
│   ├── inspector.tsx             # デバッグ・検査用UI
│   ├── logs-table.tsx            # ログテーブル
│   ├── plan-dialog.tsx           # プランダイアログ
│   ├── privacy-chat.tsx          # プライバシーチャットコンポーネント
│   │
│   └── ui/                       # shadcn/ui（編集しない）
│
├── lib/
│   ├── ai/
│   │   └── prompts.ts            # モデル別システムプロンプト定義
│   │
│   ├── supabase/
│   │   ├── client.ts             # createBrowserClient（クライアント用）
│   │   ├── server.ts             # createServerClient（サーバー用）
│   │   ├── middleware.ts         # 認証ミドルウェアヘルパー
│   │   ├── index.ts              # Supabaseエクスポート
│   │   ├── types.ts              # Supabase関連型定義
│   │   └── usage.ts              # API使用量トラッキング
│   │
│   ├── pii.ts                    # ローカルPII検出・秘匿化
│   ├── input-validation.ts       # 入力バリデーション・インジェクション検出
│   ├── types.ts                  # 共通型定義（PIIEntity, Models等）
│   ├── store.ts                  # 状態管理ストア
│   ├── sample-data.ts            # サンプルデータ
│   └── utils.ts                  # 汎用ユーティリティ（cn関数等）
│
├── hooks/
│   ├── use-mobile.ts             # モバイル検出フック
│   └── use-toast.ts              # トースト通知フック
│
├── supabase/
│   └── migrations/               # DBマイグレーション
│       ├── 001_create_profiles_and_usage.sql
│       └── 002_security_fixes.sql
│
└── middleware.ts                 # Supabase Auth ルート保護
```

---

## 実装パターン
useEffectは可能な限り使わないように。

### 1. ローカルPII検出・秘匿化（lib/pii.ts）

```typescript
import type { PIIEntity, PIIType } from "./types"

interface PIIRule {
  type: PIIType
  pattern: RegExp
  mask: string
}

const PII_RULES: PIIRule[] = [
  { type: "EMAIL", pattern: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, mask: "[EMAIL_REDACTED]" },
  { type: "PHONE", pattern: /(\+?\d{1,4}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}/g, mask: "[PHONE_REDACTED]" },
  { type: "CREDIT_CARD", pattern: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g, mask: "[CARD_REDACTED]" },
  // ... 住所、人名等
]

export function detectPII(content: string): PIIEntity[] {
  const entities: PIIEntity[] = []
  for (const rule of PII_RULES) {
    const matches = content.matchAll(rule.pattern)
    for (const match of matches) {
      if (match.index !== undefined) {
        entities.push({
          type: rule.type,
          start: match.index,
          end: match.index + match[0].length,
          confidence: generateConfidence(),
          originalText: match[0],
          maskedText: rule.mask,
        })
      }
    }
  }
  return entities.sort((a, b) => a.start - b.start)
}

export function processPII(content: string): { sanitizedContent: string; entities: PIIEntity[] } {
  const entities = detectPII(content)
  const sanitizedContent = sanitize(content, entities)
  return { sanitizedContent, entities }
}
```

### 2. チャットAPIルート（app/api/chat/route.ts）

```typescript
import { streamText } from 'ai'
import { createGoogleGenerativeAI } from '@ai-sdk/google'
import { createOpenAI } from '@ai-sdk/openai'
import { getSystemPrompt } from '@/lib/ai/prompts'
import { createClient } from '@/lib/supabase/server'
import { canMakeRequest, incrementApiUsage } from '@/lib/supabase/usage'
import { validateMessages, processUserInput, sanitizeUserInput } from '@/lib/input-validation'

export const maxDuration = 60

const google = createGoogleGenerativeAI({ apiKey: process.env.GOOGLE_API_KEY })
const openai = createOpenAI({ apiKey: process.env.OPENAI_API_KEY })

function getModel(modelId: string) {
  switch (modelId) {
    case 'gpt-5.2':
      return openai('gpt-5.2')
    case 'gemini-3-flash-preview':
    default:
      return google('gemini-3-flash-preview')
  }
}

export async function POST(req: Request) {
  // 認証チェック
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return new Response('認証が必要です', { status: 401 })
  }

  // 使用量チェック
  const usageCheck = await canMakeRequest(user.id)
  if (!usageCheck.allowed) {
    return new Response(usageCheck.reason, { status: 429 })
  }

  const { messages, model = 'gemini-3-flash-preview' } = await req.json()

  // バリデーション・サニタイズ
  const messagesValidation = validateMessages(messages)
  if (!messagesValidation.isValid) {
    return new Response(messagesValidation.error, { status: 400 })
  }

  // ストリーミング応答を生成
  const result = await streamText({
    model: getModel(model),
    system: getSystemPrompt(model),
    messages: convertedMessages,
    onFinish: async ({ usage }) => {
      if (usage) {
        const totalTokens = (usage.inputTokens || 0) + (usage.outputTokens || 0)
        await incrementApiUsage(user.id, totalTokens)
      }
    },
  })

  return result.toTextStreamResponse()
}
```

### 3. Supabaseクライアント（lib/supabase/server.ts）

```typescript
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();
  
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        },
      },
    }
  );
}
```

### 4. 使用量トラッキング（lib/supabase/usage.ts）

```typescript
import { createClient } from './server'

export async function canMakeRequest(userId: string): Promise<{ allowed: boolean; reason?: string }> {
  const supabase = await createClient()
  // 使用量の確認ロジック
  // プラン上限チェック
  return { allowed: true }
}

export async function incrementApiUsage(userId: string, tokens: number): Promise<void> {
  const supabase = await createClient()
  // 使用量の記録
}
```

### 5. 入力バリデーション（lib/input-validation.ts）

```typescript
// プロンプトインジェクション検出
export function detectPromptInjection(input: string): InjectionResult {
  // 高リスクパターンの検出
  // "ignore previous instructions", "system prompt", etc.
}

// メッセージ配列のバリデーション
export function validateMessages(messages: unknown): ValidationResult {
  // 配列形式、ロール、コンテンツ長のチェック
}

// ユーザー入力のサニタイズ
export function sanitizeUserInput(input: string): string {
  // XSS防止、制御文字削除
}
```

---

## データベーススキーマ（Supabase）

### chats テーブル

```sql
create table chats (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  title text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

### messages テーブル

```sql
create table messages (
  id uuid primary key default gen_random_uuid(),
  chat_id uuid references chats(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz default now()
);
```

---

---

## コーディング規約

### 命名規則

| 種類 | 規則 | 例 |
|------|------|-----|
| コンポーネント | PascalCase | `ChatHeader.tsx` → `export function ChatHeader()` |
| ファイル名 | kebab-case | `chat-header.tsx`, `use-chat-handler.ts` |
| 関数 | camelCase | `createChat()`, `anonymizeText()` |
| 定数 | SCREAMING_SNAKE_CASE | `PRESIDIO_API_URL` |
| 型/インターフェース | PascalCase | `type Chat`, `interface Message` |

### インポート順序

```typescript
// 1. React/Next.js
import { useState } from 'react';
import { useRouter } from 'next/navigation';

// 2. 外部ライブラリ
import { streamText } from 'ai';

// 3. 内部モジュール（エイリアス）
import { createClient } from '@/lib/supabase/server';
import { Button } from '@/components/ui/button';

// 4. 型
import type { Chat, Message } from '@/lib/types';
```

### 禁止事項

- `any`型の使用（`unknown`を使う）
- `console.log`の本番コードへの残置
- コンポーネント内での直接的なDB操作（lib/supabase/を経由する）
- `components/ui/`内のファイル編集（shadcn/uiは上書きされる）

---

## セキュリティ要件

1. **全てのチャットAPIは認証必須**（middleware.ts + Supabase Auth）
2. **入力バリデーション**：lib/input-validation.tsで処理
3. **プロンプトインジェクション検出**：高リスクパターンを検出・ブロック
4. **PIIはローカル検出で秘匿化**（lib/pii.ts）
5. **RLS（Row Level Security）有効化**：ユーザーは自分のデータのみアクセス可能
6. **環境変数にシークレットを格納**：コードにハードコードしない
7. **使用量制限**：lib/supabase/usage.tsでAPI使用量を管理

---

## 開発時の注意

- `pnpm dev`で開発サーバー起動
- 必要な環境変数（.env.example参照）：
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - `GOOGLE_API_KEY`（Gemini用）
  - `OPENAI_API_KEY`（GPT用）
- Supabaseはローカル or クラウドどちらでも可
- マイグレーションは`supabase/migrations/`に配置
