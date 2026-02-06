import os
import sys
import argparse
import re
from pathlib import Path
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer

# 設定ファイルをインポート
try:
    from . import config
except ImportError:
    import config

def setup_analyzer():
    """Presidio AnalyzerEngine を日本語サポートとカスタム Recognizer でセットアップします。"""
    # 設定ファイルから NLP 設定を取得
    provider = NlpEngineProvider(nlp_configuration=config.NLP_CONFIG)
    nlp_engine = provider.create_engine()
    
    # 日本語向けのコンテキストエンハンサーを設定
    # コンテキスト単語が見つかった場合のスコア向上率を調整
    # context_similarity_factor: コンテキストが見つかった場合のスコア増加率
    # min_score_with_context_similarity: コンテキストがある場合の最小スコア
    context_aware_enhancer = LemmaContextAwareEnhancer(
        context_similarity_factor=0.35,  # コンテキストが見つかった場合、スコアを0.35増加
        min_score_with_context_similarity=0.75  # コンテキストがある場合の最小スコアを0.75に設定
    )
    
    # 設定ファイルから閾値を取得
    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine, 
        default_score_threshold=config.DEFAULT_SCORE_THRESHOLD,
        context_aware_enhancer=context_aware_enhancer
    )

    # --- 日本語向けのカスタム Recognizer ---

    # 1. 日本の電話番号 Recognizer
    # より厳密な日本の電話番号パターン（0始まり、10〜11桁の構成を想定）
    jp_phone_pattern = Pattern(
        name="jp_phone_pattern",
        regex=r"0\d{1,4}-\d{1,4}-\d{3,4}",
        score=config.JP_PHONE_SCORE
    )
    jp_phone_recognizer = PatternRecognizer(
        supported_entity="PHONE_NUMBER",
        patterns=[jp_phone_pattern],
        context=config.CONTEXT_WORDS.get("PHONE_NUMBER"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(jp_phone_recognizer)

    # 2. メールアドレス Recognizer
    email_pattern = Pattern(
        name="email_pattern",
        regex=r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        score=config.EMAIL_SCORE
    )
    email_recognizer = PatternRecognizer(
        supported_entity="EMAIL_ADDRESS",
        patterns=[email_pattern],
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(email_recognizer)

    # 3. クレジットカード Recognizer
    cc_pattern = Pattern(
        name="cc_pattern",
        regex=r"\b(?:\d{4}-){3}\d{4}\b|\b\d{14,16}\b",
        score=config.CC_SCORE
    )
    cc_recognizer = PatternRecognizer(
        supported_entity="CREDIT_CARD",
        patterns=[cc_pattern],
        context=config.CONTEXT_WORDS.get("CREDIT_CARD"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(cc_recognizer)

    # 4. ローマ字氏名 Recognizer
    # 大文字の 苗字 名前 または 名前 苗字
    romaji_name_pattern = Pattern(
        name="romaji_name_pattern",
        regex=r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|[A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})*",
        score=config.ROMAJI_NAME_SCORE
    )
    romaji_name_recognizer = PatternRecognizer(
        supported_entity="PERSON",
        patterns=[romaji_name_pattern],
        context=config.CONTEXT_WORDS.get("PERSON"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(romaji_name_recognizer)

    # 4b. 日本語氏名 Recognizer (漢字・かな・カナ、文脈重視)
    # より柔軟なパターン：特定の記号への依存を減らし、一般的な区切り文字に対応
    jp_name_pattern = Pattern(
        name="jp_name_pattern",
        regex=r"[一-龠ぁ-んァ-ヶ]{2,15}(?:[0-9]{1,5})?",
        score=config.PERSON_SCORE
    )
    # 名前らしきものをより強く拾うための追加パターン（より汎用的な区切り文字に対応）
    # 特定の記号（「記録」など）への依存を削除し、一般的な区切り文字に変更
    jp_name_strong_pattern = Pattern(
        name="jp_name_strong_pattern",
        regex=r"(?<=[：:\s\-|])([一-龠]{2,4}\s?[一-龠ぁ-んァ-ヶ]{2,4})(?=[:：\s\n]|$)",
        score=0.85
    )
    jp_name_recognizer = PatternRecognizer(
        supported_entity="PERSON",
        patterns=[jp_name_pattern, jp_name_strong_pattern],
        context=config.CONTEXT_WORDS.get("PERSON"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(jp_name_recognizer)

    # 5. 日本の組織名 Recognizer (接尾辞による補完、より柔軟なパターン)
    # より汎用的な組織名パターン：接尾辞の前の文字列も柔軟に
    # 改行を含まないようにする（非貪欲マッチと否定先読みを使用）
    org_pattern = Pattern(
        name="org_pattern",
        regex=r"[一-龠ぁ-んァ-ヶA-Za-z0-9]{2,}(?:製作所|株式会社|有限会社|合同会社|一般社団法人|一般財団法人|特定非営利活動法人|商店|店舗|支店|ホテル|旅館|銀行|証券|会社|企業|法人)(?![\S])",
        score=config.ORG_SCORE
    )
    org_recognizer = PatternRecognizer(
        supported_entity="ORG",
        patterns=[org_pattern],
        context=config.CONTEXT_WORDS.get("ORG"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(org_recognizer)
    
    # 5b. ORGANIZATIONエンティティ用のRecognizer（Presidioが返す可能性がある形式）
    organization_recognizer = PatternRecognizer(
        supported_entity="ORGANIZATION",
        patterns=[org_pattern],
        context=config.CONTEXT_WORDS.get("ORGANIZATION"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(organization_recognizer)

    # 5c. 日本の住所 Recognizer (LOCATION)
    # 都道府県名 + 市区町村 + 番地 + 建物名のパターン
    # PresidioのデフォルトLOCATION検出と重複しないように、より具体的なパターンを使用
    # 注: PresidioのデフォルトLOCATION検出も動作するため、カスタムRecognizerは追加しない
    # 代わりに、Presidioのデフォルト検出を信頼し、コンテキスト単語で精度を向上させる

    # 6. マイナンバー Recognizer (12桁)
    mynumber_pattern = Pattern(
        name="mynumber_pattern",
        regex=r"\d{12}",
        score=config.MY_NUMBER_SCORE
    )
    mynumber_recognizer = PatternRecognizer(
        supported_entity="MY_NUMBER",
        patterns=[mynumber_pattern],
        context=config.CONTEXT_WORDS.get("MY_NUMBER"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(mynumber_recognizer)

    # 7. 運転免許証番号 Recognizer (12桁、前後の「第」「号」を許容)
    license_pattern = Pattern(
        name="license_pattern",
        regex=r"(?:第?\s*)?(\d{12})(?:\s*号)?",
        score=config.DRIVERS_LICENSE_SCORE
    )
    license_recognizer = PatternRecognizer(
        supported_entity="DRIVERS_LICENSE",
        patterns=[license_pattern],
        context=config.CONTEXT_WORDS.get("DRIVERS_LICENSE"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(license_recognizer)

    # 8. パスポート番号 Recognizer (英字1-2文字 + 数字7-8桁)
    passport_pattern = Pattern(
        name="passport_pattern",
        regex=r"[A-Z]{1,2}\d{7,8}",
        score=config.PASSPORT_SCORE
    )
    passport_recognizer = PatternRecognizer(
        supported_entity="PASSPORT",
        patterns=[passport_pattern],
        context=config.CONTEXT_WORDS.get("PASSPORT"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(passport_recognizer)

    # 9. 口座番号 Recognizer (7桁)
    bank_account_pattern = Pattern(
        name="bank_account_pattern",
        regex=r"\d{7}",
        score=config.BANK_ACCOUNT_SCORE
    )
    bank_account_recognizer = PatternRecognizer(
        supported_entity="BANK_ACCOUNT",
        patterns=[bank_account_pattern],
        context=config.CONTEXT_WORDS.get("BANK_ACCOUNT"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(bank_account_recognizer)

    # 10. 納税者番号 / 登録番号 Recognizer (T + 13桁)
    tax_number_pattern = Pattern(
        name="tax_number_pattern",
        regex=r"T\d{13}",
        score=config.TAX_NUMBER_SCORE
    )
    tax_number_recognizer = PatternRecognizer(
        supported_entity="TAX_NUMBER",
        patterns=[tax_number_pattern],
        context=config.CONTEXT_WORDS.get("TAX_NUMBER"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(tax_number_recognizer)

    # 11. パスワード Recognizer (文脈重視 + より柔軟なパターン)
    # look-behindは固定幅である必要があるため、別のアプローチを使用
    password_patterns = [
        Pattern(
            name="password_en_pattern",
            regex=r"[Pp]assword\s*[:：=]\s*(\S{8,})",
            score=0.95
        ),
        Pattern(
            name="password_ja_pattern",
            regex=r"パスワード\s*[:：=]\s*(\S{8,})",
            score=0.95
        ),
        Pattern(
            name="password_pw_pattern",
            regex=r"[Pp][Ww]\s*[:：=]\s*(\S{8,})",
            score=0.95
        )
    ]
    password_recognizer = PatternRecognizer(
        supported_entity="PASSWORD",
        patterns=password_patterns,
        context=config.CONTEXT_WORDS.get("PASSWORD"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(password_recognizer)

    # 12. Secret Key Recognizer (文脈重視 + プレフィックス対応)
    secret_key_patterns = [
        Pattern(
            name="secret_key_prefix_pattern",
            regex=r"(?:sk|pk|tok|secret|key|akid|amzn)[-_a-zA-Z0-9]{12,}",
            score=0.95
        ),
        Pattern(
            name="long_secret_pattern",
            regex=r"[a-zA-Z0-9\-_/+=.]{32,}",
            score=config.SECRET_KEY_SCORE
        )
    ]
    secret_key_recognizer = PatternRecognizer(
        supported_entity="SECRET_KEY",
        patterns=secret_key_patterns,
        context=config.CONTEXT_WORDS.get("SECRET_KEY"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(secret_key_recognizer)

    # 13. 証明書 / 秘密鍵 Recognizer (ブロック検出)
    cert_pattern = Pattern(
        name="cert_pattern",
        regex=r"-----BEGIN [\s\S]+?-----END [\s\S]+?-----",
        score=config.CERTIFICATE_SCORE
    )
    cert_recognizer = PatternRecognizer(
        supported_entity="CERTIFICATE",
        patterns=[cert_pattern],
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(cert_recognizer)

    # 14. セキュリティコード Recognizer (3-4桁、文脈重視)
    security_code_pattern = Pattern(
        name="security_code_pattern",
        regex=r"\b\d{3,4}\b",
        score=config.SECURITY_CODE_SCORE
    )
    security_code_recognizer = PatternRecognizer(
        supported_entity="SECURITY_CODE",
        patterns=[security_code_pattern],
        context=config.CONTEXT_WORDS.get("SECURITY_CODE"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(security_code_recognizer)

    # 15. 暗証番号（PIN）Recognizer (4桁、文脈必須)
    # 暗証番号は通常4桁の数字で、コンテキスト単語と一緒に出現
    pin_pattern = Pattern(
        name="pin_pattern",
        regex=r"\b\d{4}\b",
        score=config.PIN_SCORE
    )
    pin_recognizer = PatternRecognizer(
        supported_entity="PIN",
        patterns=[pin_pattern],
        context=config.CONTEXT_WORDS.get("PIN"),
        supported_language="ja"
    )
    analyzer.registry.add_recognizer(pin_recognizer)

    return analyzer

# 正規表現パターンを事前コンパイルしてパフォーマンスを向上（遅延評価で一度だけコンパイル）
_digit_only_pattern = re.compile(r'^[\d\s\-:：、。，．]+$')
_year_pattern = re.compile(r'^\d{4}$')
_common_suffixes_pattern = None

def _get_common_suffixes_pattern():
    """遅延評価で正規表現パターンをコンパイル"""
    global _common_suffixes_pattern
    if _common_suffixes_pattern is None:
        _common_suffixes_pattern = re.compile(config.COMMON_SUFFIXES_PATTERN + r'$')
    return _common_suffixes_pattern

def filter_common_words(results, text):
    """
    一般的な日本語単語をPERSONとして誤検知した結果を除外します。
    コンテキストベースの動的スコア調整も行います。
    また、重複する検出結果や包含関係にある結果を整理します。
    """
    # 重複や包含関係を整理：より長い検出結果を優先し、短い重複を削除
    results = sorted(results, key=lambda x: (x.end - x.start, -x.start), reverse=True)
    filtered_results = []
    seen_ranges = set()
    
    for result in results:
        # 重複チェック：既に処理した範囲と重複している場合はスキップ
        range_key = (result.start, result.end)
        if range_key in seen_ranges:
            continue
        
        # 包含関係チェック：既存の結果に完全に含まれている場合はスキップ
        is_contained = False
        for existing_start, existing_end in seen_ranges:
            if existing_start <= result.start and result.end <= existing_end:
                is_contained = True
                break
        if is_contained:
            continue
        # 検出されたテキストを取得
        detected_text = text[result.start:result.end].strip()
        
        # ORGANIZATION/ORGエンティティの場合、金額パターンを早期に除外
        if result.entity_type in ("ORGANIZATION", "ORG"):
            # 金額パターン（カンマを含む数字のみ）を除外
            # 例: 485,200, 1,250,000 など（数字とカンマのみのパターン）
            if re.match(r'^\d{1,3}(?:,\d{3})+$', detected_text):
                continue
            
            # 周辺テキストを確認して「金額」などのコンテキストがある場合も除外
            context_start = max(0, result.start - 15)
            context_end = min(len(text), result.end + 5)
            context_text = text[context_start:context_end]
            # 「金額」や「¥」が周辺にある場合、数字とカンマのみのパターンは金額の可能性が高い
            if ('金額' in context_text or '¥' in context_text or '合計' in context_text) and re.match(r'^\d{1,3}(?:,\d{3})+$', detected_text):
                continue
        
        # PERSONエンティティの場合のみ、一般的な単語チェックを実行
        if result.entity_type == "PERSON":
            # 一般的な日本語単語リストに含まれている場合は除外
            if detected_text in config.COMMON_JAPANESE_WORDS:
                continue
            
            # 一般的な単語パターン（数字のみ、記号のみなど）を除外
            if _digit_only_pattern.match(detected_text):
                continue
            
            # コンテキストがない場合、スコアを下げる（閾値未満なら除外）
            # 周辺テキストを確認
            context_start = max(0, result.start - 20)
            context_end = min(len(text), result.end + 20)
            context_text = text[context_start:context_end].lower()
            
            # 一般的なビジネス用語パターンを除外（より効率的な正規表現）
            # 「〜情報」「〜記録」「〜設定」などのパターン
            if _get_common_suffixes_pattern().search(detected_text):
                continue
            
            # 数字のみのパターン（年号など）を除外
            if _year_pattern.match(detected_text) and '年' not in context_text:
                continue
            
            # コンテキスト単語が周辺にない場合、スコアを下げる
            has_context = any(
                word.lower() in context_text 
                for word in config.CONTEXT_WORDS.get("PERSON", [])
            )
            
            if not has_context and result.score < 0.75:
                # コンテキストがなく、スコアが低い場合は除外
                continue
            
            # PERSONエンティティの場合も、改行を含む検出結果を修正
            detected_text = text[result.start:result.end]
            if '\n' in detected_text:
                newline_pos = detected_text.find('\n')
                # 新しい範囲で結果を作成
                from presidio_analyzer import RecognizerResult
                new_end = result.start + newline_pos
                result = RecognizerResult(
                    entity_type=result.entity_type,
                    start=result.start,
                    end=new_end,
                    score=result.score
                )
                range_key = (result.start, new_end)
                # 修正後のテキストで再度チェック（改行を除いたテキスト）
                detected_text_clean = text[result.start:result.end].strip()
                # 一般的な日本語単語リストに含まれている場合は除外
                if detected_text_clean in config.COMMON_JAPANESE_WORDS:
                    continue
                # 修正後のテキストで一般的なビジネス用語パターンをチェック
                if _get_common_suffixes_pattern().search(detected_text_clean):
                    continue
                # 修正後のテキストでコンテキストを再チェック
                context_start = max(0, result.start - 20)
                context_end = min(len(text), result.end + 20)
                context_text = text[context_start:context_end].lower()
                has_context = any(
                    word.lower() in context_text 
                    for word in config.CONTEXT_WORDS.get("PERSON", [])
                )
                if not has_context and result.score < 0.75:
                    continue
        
        # ORGANIZATION/ORGエンティティの場合、改行を含む検出結果を修正
        if result.entity_type in ("ORGANIZATION", "ORG"):
            detected_text = text[result.start:result.end]
            
            # 改行が含まれている場合、改行の前までに範囲を制限
            if '\n' in detected_text:
                newline_pos = detected_text.find('\n')
                # 新しい範囲で結果を作成
                from presidio_analyzer import RecognizerResult
                new_end = result.start + newline_pos
                result = RecognizerResult(
                    entity_type=result.entity_type,
                    start=result.start,
                    end=new_end,
                    score=result.score
                )
                range_key = (result.start, new_end)
                # 修正後のテキストで金額パターンを再チェック
                detected_text_clean = text[result.start:result.end].strip()
                if re.match(r'^\d{1,3}(?:,\d{3})+$', detected_text_clean):
                    continue
                # 周辺テキストを確認して「金額」などのコンテキストがある場合も除外
                context_start = max(0, result.start - 15)
                context_end = min(len(text), result.end + 5)
                context_text = text[context_start:context_end]
                if ('金額' in context_text or '¥' in context_text or '合計' in context_text) and re.match(r'^\d{1,3}(?:,\d{3})+$', detected_text_clean):
                    continue
        
        # 検出結果を追加
        filtered_results.append(result)
        seen_ranges.add(range_key)
    
    return filtered_results

def get_operators():
    """エンティティごとの匿名化オペレーターを設定します。"""
    
    # 複数のエンティティタイプで共通のインデックス管理を行うためのマップ
    entity_maps = {entity: {} for entity in config.TARGET_ENTITIES}
    
    def create_operator(entity_type):
        def operator(old_value, **kwargs):
            # 前後の空白を除去して一致判定の精度を上げる
            val = old_value.strip()
            # 既に別のエンティティタイプで登録されているかチェック
            # (同一人物が PERSON と LOCATION の両方で検出される等のケース対策)
            
            entity_map = entity_maps[entity_type]
            if val not in entity_map:
                # 他のマップも含めて最大のインデックスを探すのではなく、
                # そのエンティティタイプ内での登場順とする
                entity_map[val] = len(entity_map) + 1
            
            index = entity_map[val]
            return f"<{entity_type}{index}>"
        return operator

    operators = {}
    for entity in config.TARGET_ENTITIES:
        operators[entity] = OperatorConfig("custom", {"lambda": create_operator(entity)})
    
    return operators

def redact_file(analyzer, anonymizer, operators, input_path, output_path):
    """ファイルを読み込み、PII を匿名化して出力パスに書き込みます。"""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # 設定ファイルから対象エンティティを取得して分析
        results = analyzer.analyze(
            text=text, 
            language='ja', 
            entities=config.TARGET_ENTITIES,
            allow_list=config.ALLOW_LIST,
            score_threshold=config.DEFAULT_SCORE_THRESHOLD
        )

        # 一般的な日本語単語の誤検知を除外し、コンテキストベースの動的スコア調整を適用
        results = filter_common_words(results, text)
        
        # 重複する検出結果や包含関係にある結果を整理する（Presidioのデフォルト動作を補完）
        # 同一テキストに対する複数のエンティティ割り当てなどを整理
        
        # 匿名化の実行（カスタムオペレーターを使用）
        anonymized_result = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(anonymized_result.text)
        
        return True
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        # 詳細なスタックトレースを表示
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Japanese PII Redactor using Presidio")
    parser.add_argument("--input", type=str, help="Input directory containing markdown files")
    parser.add_argument("--output", type=str, help="Output directory for redacted files")
    parser.add_argument("--prefix", type=str, help="Prefix for output filenames", default="")
    parser.add_argument("--limit", type=int, help="Limit the number of files to process", default=None)
    
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    input_dir = Path(args.input) if args.input else base_dir / "test_md"
    output_dir = Path(args.output) if args.output else base_dir / "redacted"
    
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Presidio エンジンを初期化中 (閾値: {config.DEFAULT_SCORE_THRESHOLD})...")
    try:
        analyzer = setup_analyzer()
        anonymizer = AnonymizerEngine()
    except Exception as e:
        print(f"エンジンの初期化に失敗しました: {e}")
        return

    md_files = sorted(list(input_dir.glob("*.md")))
    if args.limit:
        md_files = md_files[:args.limit]
        
    print(f"{input_dir} 内に {len(md_files)} 個のマークダウンファイルが見つかりました")

    success_count = 0
    for md_file in md_files:
        output_file = output_dir / f"{args.prefix}{md_file.name}"
        # ファイルごとにインデックスをリセットしたオペレーターを取得
        current_operators = get_operators()
        if redact_file(analyzer, anonymizer, current_operators, md_file, output_file):
            success_count += 1
            if success_count % 50 == 0:
                print(f"{success_count} ファイル処理済み...")

    print(f"完了! {success_count} ファイルを匿名化しました。出力先: {output_dir}")

if __name__ == "__main__":
    main()
