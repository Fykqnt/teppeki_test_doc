#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
秘匿化ロジックの評価スクリプト
精度と処理時間を測定します。
"""

import time
import re
from pathlib import Path
from collections import defaultdict
import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from redactor.redactor import setup_analyzer, filter_common_words
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from redactor import config

def extract_pii_patterns(text):
    """
    テキストからPIIパターンを抽出して、期待されるエンティティを返す
    これは簡易的な評価のためのもので、実際のPIIを検出します
    """
    expected_entities = defaultdict(list)
    
    # メールアドレス
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    for email in emails:
        expected_entities['EMAIL_ADDRESS'].append(email)
    
    # 電話番号
    phones = re.findall(r'0\d{1,4}-\d{1,4}-\d{3,4}', text)
    for phone in phones:
        expected_entities['PHONE_NUMBER'].append(phone)
    
    # クレジットカード（簡易検出）
    cc_patterns = re.findall(r'\b(?:\d{4}-){3}\d{4}\b|\b\d{14,16}\b', text)
    for cc in cc_patterns:
        expected_entities['CREDIT_CARD'].append(cc)
    
    # パスワード（簡易検出）
    password_patterns = re.findall(r'[Pp]assword\s*[:：=]\s*(\S{8,})|パスワード\s*[:：=]\s*(\S{8,})', text)
    for match in password_patterns:
        pwd = match[0] if match[0] else match[1]
        if pwd:
            expected_entities['PASSWORD'].append(pwd)
    
    # シークレットキー（簡易検出）
    secret_patterns = re.findall(r'(?:sk|pk|tok|secret|key|akid|amzn)[-_a-zA-Z0-9]{12,}', text)
    for secret in secret_patterns:
        expected_entities['SECRET_KEY'].append(secret)
    
    return expected_entities

def evaluate_detection(analyzer, text, file_path):
    """
    単一ファイルの検出精度を評価
    """
    # 期待されるPIIを抽出
    expected_entities = extract_pii_patterns(text)
    
    # 実際の検出結果を取得
    results = analyzer.analyze(
        text=text,
        language='ja',
        entities=config.TARGET_ENTITIES,
        allow_list=config.ALLOW_LIST,
        score_threshold=config.DEFAULT_SCORE_THRESHOLD
    )
    
    # 一般的な単語のフィルタリングを適用
    results = filter_common_words(results, text)
    
    # 検出結果をエンティティタイプごとに分類
    detected_entities = defaultdict(list)
    for result in results:
        detected_text = text[result.start:result.end].strip()
        detected_entities[result.entity_type].append(detected_text)
    
    # 精度計算
    total_expected = sum(len(v) for v in expected_entities.values())
    total_detected = len(results)
    
    # True Positive, False Positive, False Negative を計算
    tp = 0  # True Positive: 正しく検出されたPII
    fp = 0  # False Positive: 誤検出
    fn = 0  # False Negative: 検出漏れ
    
    # 各エンティティタイプごとに評価
    all_entity_types = set(expected_entities.keys()) | set(detected_entities.keys())
    
    for entity_type in all_entity_types:
        expected = set(expected_entities.get(entity_type, []))
        detected = set(detected_entities.get(entity_type, []))
        
        # True Positive: 期待されるPIIが検出された
        tp += len(expected & detected)
        # False Positive: 検出されたが期待されていない
        fp += len(detected - expected)
        # False Negative: 期待されたが検出されなかった
        fn += len(expected - detected)
    
    # 一般的な日本語単語の誤検知をカウント
    common_word_fp = 0
    for result in results:
        detected_text = text[result.start:result.end].strip()
        if detected_text in config.COMMON_JAPANESE_WORDS:
            common_word_fp += 1
    
    return {
        'file': file_path.name,
        'total_expected': total_expected,
        'total_detected': total_detected,
        'tp': tp,
        'fp': fp,
        'fn': fn,
        'common_word_fp': common_word_fp,
        'precision': tp / (tp + fp) if (tp + fp) > 0 else 0.0,
        'recall': tp / (tp + fn) if (tp + fn) > 0 else 0.0,
        'f1': 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0,
    }

def evaluate_all(test_dir, limit=None):
    """
    すべてのテストファイルを評価
    """
    test_path = Path(test_dir)
    md_files = sorted(list(test_path.glob("*.md")))
    
    if limit:
        md_files = md_files[:limit]
    
    print(f"評価対象ファイル数: {len(md_files)}")
    print("=" * 80)
    
    # Analyzerを初期化
    print("Analyzerを初期化中...")
    analyzer = setup_analyzer()
    
    # 評価結果を格納
    all_results = []
    total_processing_time = 0
    
    # 各ファイルを評価
    for i, md_file in enumerate(md_files, 1):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 処理時間を測定
            start_time = time.time()
            result = evaluate_detection(analyzer, text, md_file)
            processing_time = time.time() - start_time
            total_processing_time += processing_time
            
            result['processing_time'] = processing_time
            all_results.append(result)
            
            if i % 10 == 0:
                print(f"処理済み: {i}/{len(md_files)} ファイル")
        
        except Exception as e:
            print(f"エラー ({md_file.name}): {e}")
            continue
    
    # 集計結果を計算
    total_tp = sum(r['tp'] for r in all_results)
    total_fp = sum(r['fp'] for r in all_results)
    total_fn = sum(r['fn'] for r in all_results)
    total_common_word_fp = sum(r['common_word_fp'] for r in all_results)
    
    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = 2 * total_tp / (2 * total_tp + total_fp + total_fn) if (2 * total_tp + total_fp + total_fn) > 0 else 0.0
    
    avg_processing_time = total_processing_time / len(all_results) if all_results and total_processing_time > 0 else 0
    
    # 結果を表示
    print("\n" + "=" * 80)
    print("評価結果サマリー")
    print("=" * 80)
    print(f"評価ファイル数: {len(all_results)}")
    print(f"\n検出結果:")
    print(f"  True Positive (TP): {total_tp}")
    print(f"  False Positive (FP): {total_fp}")
    print(f"  False Negative (FN): {total_fn}")
    print(f"  一般的な単語の誤検知: {total_common_word_fp}")
    print(f"\n精度指標:")
    print(f"  Precision (適合率): {overall_precision * 100:.2f}%")
    print(f"  Recall (再現率): {overall_recall * 100:.2f}%")
    print(f"  F1-Score: {overall_f1 * 100:.2f}%")
    print(f"\n処理時間:")
    print(f"  総処理時間: {total_processing_time:.2f}秒")
    print(f"  平均処理時間: {avg_processing_time * 1000:.2f}ミリ秒/ファイル")
    print(f"  処理速度: {len(all_results) / total_processing_time:.2f}ファイル/秒")
    print("=" * 80)
    
    # 詳細結果をファイルに保存
    output_file = Path(__file__).parent.parent / "evaluation_results.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("評価結果詳細\n")
        f.write("=" * 80 + "\n\n")
        for result in all_results:
            f.write(f"ファイル: {result['file']}\n")
            f.write(f"  TP: {result['tp']}, FP: {result['fp']}, FN: {result['fn']}\n")
            f.write(f"  Precision: {result['precision'] * 100:.2f}%, Recall: {result['recall'] * 100:.2f}%, F1: {result['f1'] * 100:.2f}%\n")
            f.write(f"  処理時間: {result['processing_time'] * 1000:.2f}ms\n\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("集計結果\n")
        f.write("=" * 80 + "\n")
        f.write(f"Precision: {overall_precision * 100:.2f}%\n")
        f.write(f"Recall: {overall_recall * 100:.2f}%\n")
        f.write(f"F1-Score: {overall_f1 * 100:.2f}%\n")
        f.write(f"平均処理時間: {avg_processing_time * 1000:.2f}ms/ファイル\n")
    
    print(f"\n詳細結果を保存しました: {output_file}")
    
    return {
        'precision': overall_precision,
        'recall': overall_recall,
        'f1': overall_f1,
        'avg_processing_time': avg_processing_time,
        'total_processing_time': total_processing_time,
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="秘匿化ロジックの評価")
    parser.add_argument("--input", type=str, help="テストファイルのディレクトリ", default="test_md")
    parser.add_argument("--limit", type=int, help="評価するファイル数の上限", default=None)
    
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent
    test_dir = base_dir / args.input
    
    evaluate_all(test_dir, limit=args.limit)
