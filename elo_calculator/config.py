"""
Configuration for LOL ELO System
Optimized values from hyperparameter search
"""

# ============================================================================
# DATA SOURCE
# ============================================================================

SHEET_ID = "1nRTW0IemmuWZ0LClblXwGbnbCKHQsdJU48z7PoPvrHM"
MATCHES_SHEET = "Matches"


# ============================================================================
# ELO PARAMETERS (OPTIMIZED)
# ============================================================================

# K-Factor: Controls how much ratings change per match
# Optimized value from grid search: K=24 performs best
K_FACTOR = 24

# Initial ELO rating for new teams
INITIAL_ELO = 1500


# ============================================================================
# SCALE FACTORS (OPTIMIZED)
# ============================================================================

# Enable scale factors (match closeness adjustment)
USE_SCALE_FACTORS = True

# Scale factor preset: 'conservative'
# Philosophy: Only stomps get full weight, close matches are heavily discounted
# 
# Rationale:
# - A 3-0 win shows dominant performance → full K-factor
# - A 3-2 win is barely better than a loss → reduced K-factor
# - This prevents overreacting to lucky/close wins
SCALE_FACTORS = {
    '1-0': 1.00,  # Bo1 - always full weight
    
    # Bo3
    '2-0': 1.00,  # Stomp - full weight
    '2-1': 0.50,  # Close - HEAVILY reduced (conservative)
    
    # Bo5
    '3-0': 1.00,  # Complete stomp - full weight
    '3-1': 0.90,  # Dominant - slightly reduced
    '3-2': 0.80,  # Close series - moderately reduced
}


# ============================================================================
# VALIDATION
# ============================================================================

# Train/Test split for temporal validation
# 70% for training, 30% for testing (chronologically)
TRAIN_TEST_SPLIT = 0.7


# ============================================================================
# PERFORMANCE METRICS (from optimization)
# ============================================================================

# Expected performance with optimized config:
# - Test Accuracy: ~70.46%
# - Train Accuracy: ~69.22%
# - Overfitting: -1.24% (negative = test better than train, excellent!)
# - Brier Score: ~0.159
# - High Confidence Accuracy: ~83.7%

# Improvement over baseline (K=20, no scale):
# - Baseline: 69.85%
# - Optimized: 70.46%
# - Improvement: +0.61 percentage points


# ============================================================================
# ALTERNATIVE CONFIGURATIONS (for reference)
# ============================================================================

# If you prefer simplicity over maximum accuracy:
# K_FACTOR = 16
# USE_SCALE_FACTORS = False
# Expected accuracy: ~70.15% (only -0.31pp worse, but simpler)