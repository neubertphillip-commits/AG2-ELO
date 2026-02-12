"""
Master Validation Report Generator
Runs all validation and analysis scripts and generates comprehensive report
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime
from typing import Dict

from core.unified_data_loader import UnifiedDataLoader

# Import all analysis modules
sys.path.append(str(Path(__file__).parent.parent / 'validation'))
sys.path.append(str(Path(__file__).parent.parent / 'analysis'))

from validation.k_fold_validation import run_k_fold_validation
from validation.bootstrap_ci import analyze_cross_regional_ci
from analysis.feature_importance import run_feature_importance_analysis
from analysis.error_patterns import analyze_error_patterns


def generate_comprehensive_report(output_file: str = "reports/validation_report.md"):
    """
    Generate comprehensive validation report

    Args:
        output_file: Output markdown file path
    """
    print("="*70)
    print("COMPREHENSIVE VALIDATION REPORT GENERATOR")
    print("="*70)
    print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create reports directory
    Path("reports").mkdir(exist_ok=True)

    # Load data
    print("\n" + "="*70)
    print("LOADING DATA")
    print("="*70)

    with UnifiedDataLoader() as loader:
        df = loader.load_matches(source='auto')
        source_info = loader.get_source_info()

    print(f"\n[OK] Loaded {len(df)} matches")
    print(f"  Source: {'Database' if source_info['has_database'] else 'Google Sheets'}")

    if source_info['has_database']:
        db_stats = source_info['database_stats']
        print(f"  Teams: {db_stats['total_teams']}")
        print(f"  Players: {db_stats.get('total_players', 'N/A')}")
        print(f"  Date Range: {db_stats['date_range'][0]} to {db_stats['date_range'][1]}")

    # Initialize report
    report = []

    report.append("# LOL ELO SYSTEM - VALIDATION REPORT")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n**Data Source:** {'Database' if source_info['has_database'] else 'Google Sheets'}")
    report.append(f"\n**Total Matches:** {len(df)}")

    if source_info['has_database']:
        db_stats = source_info['database_stats']
        report.append(f"\n**Date Range:** {db_stats['date_range'][0]} to {db_stats['date_range'][1]}")
        report.append(f"\n**Total Teams:** {db_stats['total_teams']}")

    report.append("\n" + "="*70 + "\n")

    # 1. K-Fold Cross-Validation
    print("\n" + "="*70)
    print("RUNNING K-FOLD CROSS-VALIDATION")
    print("="*70)

    try:
        k_fold_results = run_k_fold_validation(k=5)

        report.append("\n## 1. K-Fold Cross-Validation (k=5)")
        report.append(f"\n**Mean Accuracy:** {k_fold_results['mean_accuracy']:.2f}%")
        report.append(f"\n**Std Deviation:** {k_fold_results['std_accuracy']:.2f}%")
        report.append(f"\n**95% CI:** [{k_fold_results['ci_95'][0]:.2f}%, {k_fold_results['ci_95'][1]:.2f}%]")

        report.append("\n\n### Per-Fold Results:")
        report.append("\n| Fold | Accuracy |")
        report.append("|------|----------|")
        for i, fold_result in enumerate(k_fold_results['folds'], 1):
            report.append(f"| {i} | {fold_result['accuracy']:.2f}% |")

        # Interpretation
        std = k_fold_results['std_accuracy']
        if std < 2.0:
            interpretation = "[PASS] **Very Robust** - System performs consistently across time periods"
        elif std < 5.0:
            interpretation = "[PASS] **Robust** - Minor variations across time periods"
        elif std < 10.0:
            interpretation = "[WARNING] **Moderate** - Performance depends on time period"
        else:
            interpretation = "[FAIL] **High Variation** - System may be overfitting"

        report.append(f"\n\n**Interpretation:** {interpretation}")

    except Exception as e:
        print(f"[WARNING]  K-Fold validation failed: {e}")
        report.append("\n## 1. K-Fold Cross-Validation")
        report.append(f"\n[FAIL] **Failed:** {str(e)}")

    # 2. Bootstrap CI
    print("\n" + "="*70)
    print("RUNNING BOOTSTRAP CONFIDENCE INTERVALS")
    print("="*70)

    try:
        bootstrap_results = analyze_cross_regional_ci(df, n_iterations=1000)

        report.append("\n\n## 2. Bootstrap Confidence Intervals")

        overall = bootstrap_results['overall']
        report.append(f"\n### Overall Accuracy:")
        report.append(f"\n- **Accuracy:** {overall['accuracy']:.2f}%")
        report.append(f"- **95% CI:** [{overall['ci_lower']:.2f}%, {overall['ci_upper']:.2f}%]")
        report.append(f"- **Margin of Error:** ±{(overall['ci_upper'] - overall['ci_lower']) / 2:.2f}%")
        report.append(f"- **Samples:** {overall['n_samples']}")

        if bootstrap_results['cross_regional']:
            cr = bootstrap_results['cross_regional']
            report.append(f"\n### Cross-Regional Accuracy:")
            report.append(f"\n- **Accuracy:** {cr['accuracy']:.2f}%")
            report.append(f"- **95% CI:** [{cr['ci_lower']:.2f}%, {cr['ci_upper']:.2f}%]")
            report.append(f"- **Margin of Error:** ±{(cr['ci_upper'] - cr['ci_lower']) / 2:.2f}%")
            report.append(f"- **Samples:** {cr['n_samples']}")

            if cr['n_samples'] < 50:
                report.append(f"\n[WARNING] **Warning:** Small sample size - need more international tournament data")
            elif cr['n_samples'] < 100:
                report.append(f"\n[WARNING] **Note:** Moderate sample size - margin of error is significant")
            else:
                report.append(f"\n[PASS] **Good:** Sufficient sample size for reliable estimates")

    except Exception as e:
        print(f"[WARNING]  Bootstrap CI failed: {e}")
        report.append("\n\n## 2. Bootstrap Confidence Intervals")
        report.append(f"\n[FAIL] **Failed:** {str(e)}")

    # 3. Feature Importance
    print("\n" + "="*70)
    print("RUNNING FEATURE IMPORTANCE ANALYSIS")
    print("="*70)

    try:
        feature_results = run_feature_importance_analysis(df)

        report.append("\n\n## 3. Feature Importance (Ablation Study)")

        report.append("\n\n| Configuration | Train Acc | Test Acc | Overfitting | vs Baseline |")
        report.append("|---------------|-----------|----------|-------------|-------------|")

        baseline_acc = next(r['test_accuracy'] for r in feature_results if r['config'] == 'Baseline')

        for r in sorted(feature_results, key=lambda x: x['test_accuracy'], reverse=True):
            improvement = r['test_accuracy'] - baseline_acc
            improvement_str = f"+{improvement:.2f}%" if improvement >= 0 else f"{improvement:.2f}%"

            report.append(f"| {r['config']} | {r['train_accuracy']:.2f}% | {r['test_accuracy']:.2f}% | "
                         f"{r['overfitting']:+.2f}% | {improvement_str} |")

        # Incremental improvements
        report.append("\n\n### Incremental Improvements:")
        for i in range(1, len(feature_results)):
            prev = feature_results[i-1]
            curr = feature_results[i]
            delta = curr['test_accuracy'] - prev['test_accuracy']

            report.append(f"\n- **{prev['config']} → {curr['config']}:** "
                         f"{delta:+.2f}% ({prev['test_accuracy']:.2f}% → {curr['test_accuracy']:.2f}%)")

    except Exception as e:
        print(f"[WARNING]  Feature importance failed: {e}")
        report.append("\n\n## 3. Feature Importance")
        report.append(f"\n❌ **Failed:** {str(e)}")

    # 4. Error Patterns
    print("\n" + "="*70)
    print("RUNNING ERROR PATTERN ANALYSIS")
    print("="*70)

    try:
        error_results = analyze_error_patterns(df)

        report.append("\n\n## 4. Error Pattern Analysis")

        # By ELO difference
        report.append("\n\n### Accuracy by ELO Difference:")
        report.append("\n| Category | Accuracy | Samples |")
        report.append("|----------|----------|---------|")

        for category, stats in sorted(error_results['by_elo_diff'].items()):
            acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report.append(f"| {category} | {acc:.2f}% | {stats['total']} |")

        # By match closeness
        report.append("\n\n### Accuracy by Match Closeness:")
        report.append("\n| Type | Accuracy | Samples |")
        report.append("|------|----------|---------|")

        for closeness, stats in error_results['by_closeness'].items():
            acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report.append(f"| {closeness} | {acc:.2f}% | {stats['total']} |")

        # Top tournaments
        report.append("\n\n### Top Tournaments (by sample size):")
        report.append("\n| Tournament | Accuracy | Samples |")
        report.append("|------------|----------|---------|")

        sorted_tournaments = sorted(error_results['by_tournament'].items(),
                                   key=lambda x: x[1]['total'], reverse=True)[:10]

        for tournament, stats in sorted_tournaments:
            acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report.append(f"| {tournament[:40]} | {acc:.2f}% | {stats['total']} |")

    except Exception as e:
        print(f"[WARNING]  Error pattern analysis failed: {e}")
        report.append("\n\n## 4. Error Pattern Analysis")
        report.append(f"\n❌ **Failed:** {str(e)}")

    # Summary
    report.append("\n\n" + "="*70)
    report.append("\n## Summary")
    report.append("\n\nThis comprehensive validation report provides:")
    report.append("\n- **Robustness:** K-Fold CV shows system stability across time")
    report.append("\n- **Confidence:** Bootstrap CI quantifies prediction uncertainty")
    report.append("\n- **Understanding:** Feature importance shows what drives performance")
    report.append("\n- **Insights:** Error patterns reveal where system struggles")

    report.append("\n\n### Recommendations:")
    report.append("\n1. If std deviation < 5%: System is robust [PASS]")
    report.append("\n2. If cross-regional samples < 100: Import more international data [IMPORT]")
    report.append("\n3. Check feature importance to prioritize improvements [CHECK]")
    report.append("\n4. Review error patterns to identify weaknesses [WARNING]")

    report.append(f"\n\n---\n\n*Report generated by LOL ELO System Validation Suite*")

    # Write report
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print("\n" + "="*70)
    print("REPORT GENERATION COMPLETE")
    print("="*70)
    print(f"\n[OK] Report saved to: {output_file}")

    return output_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate Comprehensive Validation Report')
    parser.add_argument('--output', type=str, default='reports/validation_report.md',
                       help='Output file path (default: reports/validation_report.md)')

    args = parser.parse_args()

    report_file = generate_comprehensive_report(output_file=args.output)

    print(f"\n[REPORT] View report: {report_file}")
