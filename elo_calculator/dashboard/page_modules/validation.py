"""
Validation Suite Page - Run and view validation tests
"""

import streamlit as st
import pandas as pd
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def show():
    """Display validation suite page"""

    st.title("📈 Validation Suite")
    st.markdown("Statistical validation and performance metrics")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Validation Dashboard",
        "🔄 K-Fold Cross-Validation",
        "📉 Bootstrap Confidence Intervals",
        "⚙️ Run Validation"
    ])

    # === TAB 1: VALIDATION DASHBOARD ===
    with tab1:
        st.subheader("📊 Validation Dashboard")
        st.markdown("Overview of all validation metrics and results")

        # Check for validation report
        report_path = Path("reports/validation_report.md")

        if report_path.exists():
            st.markdown('<div class="success-box">✓ Validation report available</div>', unsafe_allow_html=True)

            # Read and display report
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()

            with st.expander("📄 View Full Validation Report", expanded=False):
                st.markdown(report_content)

            # Quick metrics
            st.markdown("---")
            st.subheader("🎯 Quick Metrics")

            # Try to load individual result files
            col1, col2, col3 = st.columns(3)

            # K-Fold results
            with col1:
                kfold_path = Path("validation/k_fold_results_k5.json")
                if kfold_path.exists():
                    try:
                        with open(kfold_path, 'r') as f:
                            kfold_data = json.load(f)

                        st.metric(
                            "K-Fold Accuracy (K=5)",
                            f"{kfold_data.get('mean_accuracy', 0):.2f}%",
                            delta=f"±{kfold_data.get('std_accuracy', 0):.2f}%"
                        )
                        st.caption(f"Std Dev: {kfold_data.get('std_accuracy', 0):.2f}%")
                    except:
                        st.info("K-Fold results not available")
                else:
                    st.info("K-Fold results not available")

            # Bootstrap results
            with col2:
                bootstrap_path = Path("validation/bootstrap_results_1000.json")
                if bootstrap_path.exists():
                    try:
                        with open(bootstrap_path, 'r') as f:
                            bootstrap_data = json.load(f)

                        st.metric(
                            "Bootstrap Accuracy",
                            f"{bootstrap_data.get('mean_accuracy', 0):.2%}",
                            delta=f"±{bootstrap_data.get('margin_of_error', 0):.2%}"
                        )
                        st.caption(f"95% CI: [{bootstrap_data.get('ci_lower', 0):.2%}, {bootstrap_data.get('ci_upper', 0):.2%}]")
                    except:
                        st.info("Bootstrap results not available")
                else:
                    st.info("Bootstrap results not available")

            # Feature importance
            with col3:
                feature_path = Path("analysis/feature_importance.json")
                if feature_path.exists():
                    try:
                        with open(feature_path, 'r') as f:
                            feature_data = json.load(f)

                        features = feature_data.get('features', {})
                        if features:
                            best_feature = max(features.items(), key=lambda x: x[1].get('accuracy', 0))
                            st.metric(
                                "Best Configuration",
                                best_feature[0],
                                delta=f"{best_feature[1].get('accuracy', 0):.2%}"
                            )
                            st.caption("See Analysis tab for details")
                    except:
                        st.info("Feature importance not available")
                else:
                    st.info("Feature importance not available")

        else:
            st.markdown('<div class="warning-box">⚠️ No validation report found. Run validation first!</div>', unsafe_allow_html=True)
            st.markdown("""
            **To generate validation report:**
            1. Navigate to **⚙️ Run Validation** tab
            2. Click "Generate Master Validation Report"
            3. Wait for analysis to complete
            4. View results here

            Or run from command line:
            ```bash
            python scripts/generate_validation_report.py
            ```
            """)

    # === TAB 2: K-FOLD CROSS-VALIDATION ===
    with tab2:
        st.subheader("🔄 K-Fold Cross-Validation")
        st.markdown("Temporal cross-validation results")

        st.info("""
        **What is K-Fold Cross-Validation?**

        K-Fold splits the data into K parts, trains on earlier parts, and tests on later parts.
        This ensures we test on "future" data, avoiding data leakage.

        **Why Temporal?**
        Standard K-Fold randomly splits data, which lets the model "see the future".
        Temporal K-Fold respects time order: always train on past, test on future.
        """)

        # Check for results
        k5_path = Path("validation/k_fold_results_k5.json")
        k10_path = Path("validation/k_fold_results_k10.json")

        results_available = []
        if k5_path.exists():
            results_available.append(("K=5", k5_path))
        if k10_path.exists():
            results_available.append(("K=10", k10_path))

        if results_available:
            # Select which results to view
            selected = st.selectbox(
                "Select K-Fold Configuration",
                [name for name, _ in results_available]
            )

            # Load selected results
            selected_path = next(path for name, path in results_available if name == selected)

            try:
                with open(selected_path, 'r') as f:
                    results = json.load(f)

                # Display metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("K Folds", results.get('k', 'N/A'))

                with col2:
                    st.metric("Mean Accuracy", f"{results.get('mean_accuracy', 0):.2f}%")

                with col3:
                    st.metric("Std Deviation", f"{results.get('std_dev', 0):.3f}%")

                with col4:
                    st.metric("Margin of Error", f"±{results.get('margin_of_error', 0):.2f}%")

                # Fold-by-fold results
                st.markdown("---")
                st.subheader("Fold-by-Fold Results")

                fold_accuracies = results.get('fold_accuracies', [])
                if fold_accuracies:
                    fold_df = pd.DataFrame({
                        'Fold': [f"Fold {i+1}" for i in range(len(fold_accuracies))],
                        'Accuracy': fold_accuracies
                    })

                    # Bar chart
                    st.bar_chart(
                        fold_df.set_index('Fold')['Accuracy'],
                        use_container_width=True
                    )

                    # Table
                    fold_df['Accuracy'] = fold_df['Accuracy'].apply(lambda x: f"{x:.2%}")
                    st.dataframe(fold_df, use_container_width=True, hide_index=True)

                # Interpretation
                st.markdown("---")
                st.subheader("📊 Interpretation")

                std_dev = results.get('std_dev', 0)
                if std_dev < 0.01:
                    stability = "Very Stable"
                    color = "green"
                elif std_dev < 0.02:
                    stability = "Stable"
                    color = "blue"
                else:
                    stability = "Variable"
                    color = "orange"

                st.markdown(f"**Model Stability:** <span style='color: {color}; font-weight: bold;'>{stability}</span>", unsafe_allow_html=True)
                st.markdown(f"Low standard deviation ({std_dev:.3%}) indicates consistent performance across time periods.")

            except Exception as e:
                st.error(f"Error loading results: {str(e)}")

        else:
            st.warning("No K-Fold results found. Run validation first!")

    # === TAB 3: BOOTSTRAP CONFIDENCE INTERVALS ===
    with tab3:
        st.subheader("📉 Bootstrap Confidence Intervals")
        st.markdown("Statistical confidence intervals via bootstrap resampling")

        st.info("""
        **What is Bootstrap?**

        Bootstrap creates many "resampled" datasets by sampling with replacement.
        Each resample is used to calculate accuracy, building a distribution.
        The 95% confidence interval is the middle 95% of this distribution.

        **Why Bootstrap?**
        - Doesn't assume normal distribution
        - Works with small samples
        - Provides robust confidence intervals
        """)

        # Check for results
        bootstrap_path = Path("validation/bootstrap_results_1000.json")

        if bootstrap_path.exists():
            try:
                with open(bootstrap_path, 'r') as f:
                    results = json.load(f)

                # Display metrics
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Iterations", f"{results.get('iterations', 0):,}")

                with col2:
                    st.metric("Mean Accuracy", f"{results.get('mean_accuracy', 0):.2%}")

                with col3:
                    st.metric("Margin of Error", f"±{results.get('margin_of_error', 0):.2%}")

                # Confidence interval
                st.markdown("---")
                st.subheader("95% Confidence Interval")

                ci_lower = results.get('ci_lower', 0)
                ci_upper = results.get('ci_upper', 0)
                mean_acc = results.get('mean_accuracy', 0)

                st.markdown(f"""
                We are **95% confident** that the true accuracy is between:

                **{ci_lower:.2%}** and **{ci_upper:.2%}**

                (Mean: **{mean_acc:.2%}**)
                """)

                # Visualization
                import numpy as np

                # Create simple visualization
                ci_data = pd.DataFrame({
                    'Metric': ['Lower Bound', 'Mean', 'Upper Bound'],
                    'Value': [ci_lower, mean_acc, ci_upper]
                })

                st.bar_chart(
                    ci_data.set_index('Metric')['Value'],
                    use_container_width=True
                )

                # Interpretation
                st.markdown("---")
                st.subheader("📊 Interpretation")

                interval_width = ci_upper - ci_lower
                if interval_width < 0.03:
                    precision = "Very Precise"
                    color = "green"
                elif interval_width < 0.05:
                    precision = "Precise"
                    color = "blue"
                else:
                    precision = "Moderate Precision"
                    color = "orange"

                st.markdown(f"**Estimate Precision:** <span style='color: {color}; font-weight: bold;'>{precision}</span>", unsafe_allow_html=True)
                st.markdown(f"Narrow confidence interval (width: {interval_width:.2%}) indicates sufficient sample size.")

            except Exception as e:
                st.error(f"Error loading results: {str(e)}")

        else:
            st.warning("No bootstrap results found. Run validation first!")

    # === TAB 4: RUN VALIDATION ===
    with tab4:
        st.subheader("⚙️ Run Validation")
        st.markdown("Execute validation tests (may take several minutes)")

        st.warning("⚠️ Running validation tests will execute Python scripts. Ensure data is imported first!")

        # Master validation report
        st.markdown("---")
        st.subheader("📊 Master Validation Report")
        st.markdown("Comprehensive report including all validation tests")

        if st.button("🚀 Generate Master Validation Report", type="primary"):
            st.info("Generating master validation report... This may take 2-5 minutes.")

            with st.spinner("Running all validation tests..."):
                import subprocess

                try:
                    result = subprocess.run(
                        ["python", "scripts/generate_validation_report.py"],
                        capture_output=True,
                        text=True,
                        timeout=600  # 10 minute timeout
                    )

                    if result.returncode == 0:
                        st.success("✓ Validation report generated successfully!")
                        st.markdown("Navigate to **📊 Validation Dashboard** tab to view results.")

                        # Show output
                        with st.expander("View Script Output"):
                            st.code(result.stdout)
                    else:
                        st.error("❌ Validation failed!")
                        st.code(result.stderr)

                except subprocess.TimeoutExpired:
                    st.error("❌ Validation timed out (>10 minutes). Check your dataset size.")
                except Exception as e:
                    st.error(f"❌ Error running validation: {str(e)}")

        # Individual tests
        st.markdown("---")
        st.subheader("🔧 Individual Tests")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**K-Fold Cross-Validation**")

            k_value = st.selectbox("K Value", [5, 10], index=0, key="kfold_k")

            if st.button("Run K-Fold Validation"):
                st.info(f"Running K-Fold validation with K={k_value}...")

                with st.spinner("Running..."):
                    import subprocess

                    try:
                        result = subprocess.run(
                            ["python", "validation/k_fold_validation.py", "--k", str(k_value)],
                            capture_output=True,
                            text=True,
                            timeout=300
                        )

                        if result.returncode == 0:
                            st.success(f"✓ K-Fold (K={k_value}) completed!")
                            with st.expander("View Output"):
                                st.code(result.stdout)
                        else:
                            st.error("❌ K-Fold validation failed!")
                            st.code(result.stderr)

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        with col2:
            st.markdown("**Bootstrap Confidence Intervals**")

            iterations = st.selectbox("Iterations", [100, 1000, 10000], index=1, key="bootstrap_iter")

            if st.button("Run Bootstrap"):
                st.info(f"Running bootstrap with {iterations} iterations...")

                with st.spinner("Running..."):
                    import subprocess

                    try:
                        result = subprocess.run(
                            ["python", "validation/bootstrap_ci.py", "--iterations", str(iterations)],
                            capture_output=True,
                            text=True,
                            timeout=300
                        )

                        if result.returncode == 0:
                            st.success(f"✓ Bootstrap ({iterations} iterations) completed!")
                            with st.expander("View Output"):
                                st.code(result.stdout)
                        else:
                            st.error("❌ Bootstrap validation failed!")
                            st.code(result.stderr)

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        # Command line reference
        st.markdown("---")
        st.subheader("💻 Command Line Reference")

        st.markdown("""
        **Run validation from terminal:**

        ```bash
        # Master report (recommended)
        python scripts/generate_validation_report.py

        # Individual tests
        python validation/k_fold_validation.py --k 5
        python validation/bootstrap_ci.py --iterations 1000
        python analysis/feature_importance.py
        python analysis/error_patterns.py
        ```

        **View results:**

        ```bash
        # Master report
        cat reports/validation_report.md

        # Individual results (JSON)
        cat validation/k_fold_results_k5.json | python -m json.tool
        cat validation/bootstrap_results_1000.json | python -m json.tool
        ```
        """)


if __name__ == "__main__":
    show()
