# Prototype Scale Definition
## Protector Uttam: MVP Demonstration Architecture

**Document Type:** Technical Specification - Prototype Scope  
**Version:** 1.0  
**Date:** 2024  
**Scope:** MVP Demonstration (NOT Production Scale)  

---

## Executive Summary

This document defines the **minimum viable prototype (MVP)** for Protector Uttam. The prototype is designed to:

✅ **Demonstrate** the core trust-scoring concept with real federated learning  
✅ **Validate** the 5-dimensional trust model against synthetic scenarios  
✅ **Run locally** on a single development machine  
✅ **Complete rapidly** (proof-of-concept in weeks, not months)  

❌ **NOT designed to:** Support millions of participants, process terabytes of data, or demonstrate production scalability

---

## 1. MVP Prototype Configuration

### 1.1 Core Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Simulated Participants** | 10 | Direct file-to-participant mapping from dataset |
| **Federated Rounds** | 5-10 | Enough to test gradient aggregation + poisoning detection |
| **Baseline Model** | Gradient Boosting Classifier | Single model, moderate complexity, generates real gradients |
| **Dataset** | 13,910 samples across 10 files | Existing dataset, no additional collection |
| **Feature Dimensionality** | 128 continuous features | Fixed, no dynamic expansion |
| **Prediction Task** | 6-class multiclass classification | Defined, no multi-task learning |
| **Coordinator Model** | Single Python process | Centralized, no distribution |
| **Scenario Count** | 9 controlled scenarios | Pre-defined, injected for validation |

### 1.2 Participant Configuration

```python
# MVP Federated Setup
participants = {
    "org_1": {"data": batch1.dat, "samples": 445, "balance": "3.27×"},
    "org_2": {"data": batch2.dat, "samples": 1244, "balance": "106.4× SEVERE"},
    "org_3": {"data": batch3.dat, "samples": 1586, "balance": "2.27×"},
    "org_4": {"data": batch4.dat, "samples": 161, "balance": "5.33× SMALL"},
    "org_5": {"data": batch5.dat, "samples": 197, "balance": "3.15× SMALL"},
    "org_6": {"data": batch6.dat, "samples": 2300, "balance": "20.90× SEVERE"},
    "org_7": {"data": batch7.dat, "samples": 3613, "balance": "2.07× LARGEST"},
    "org_8": {"data": batch8.dat, "samples": 294, "balance": "7.94×"},
    "org_9": {"data": batch9.dat, "samples": 470, "balance": "1.84×"},
    "org_10": {"data": batch10.dat, "samples": 3600, "balance": "1.00× PERFECT"},
}

# Participant Distribution
min_participant_size = 161 samples  # batch4
max_participant_size = 3,613 samples # batch7
avg_participant_size = 1,391 samples
total_samples = 13,910
```

### 1.3 Federated Round Architecture

**Each Round:**
1. **Broadcast** global model to all participants (10)
2. **Local Training** at each participant (10 parallel or sequential)
3. **Gradient Extraction** from local models
4. **Trust Scoring** on each update (5-dimension scoring)
5. **Confidence Assessment** on each update (5-component scoring)
6. **Decision Making** (ALLOW/MONITOR/REVIEW/BLOCK)
7. **Aggregation** of trusted updates only
8. **Model Update** at coordinator

**Round Duration (Single Machine):**
- Broadcast: <100ms
- Local training: 5-30 seconds per participant (sequential)
- Gradient extraction: 1-5 seconds
- Trust scoring: 2-10 seconds
- Aggregation: <1 second
- **Total per round: 1-5 minutes** (sequential training)

---

## 2. Hardware Requirements

### 2.1 Minimum MVP Hardware

```
Machine Type: Laptop or Desktop Workstation

CPU:
  - Intel Core i7 / AMD Ryzen 7 or equivalent
  - 4+ cores (can use parallelization in Stage 3)
  - Single core sufficient for sequential MVP

Memory:
  - 8 GB RAM (minimum)
  - 16 GB RAM (recommended for comfortable operation)

Storage:
  - 50 GB free space
  - SSD preferred (faster data loading)
  - HDD acceptable (slower iterations)

Network:
  - None required (single machine)
  - Localhost communication only

GPU:
  - Not required for MVP
  - Not required for gradient boosting
  - Can accelerate XGBoost/CatBoost in Stage 3+
```

### 2.2 Recommended Development Hardware

```
Machine Type: Developer Workstation or Small Server

CPU:
  - Intel Core i9 / AMD Ryzen 9 or equivalent
  - 8+ cores for parallelized training
  - Hyperthreading beneficial

Memory:
  - 32 GB RAM (enables multi-participant parallelization)
  - Reduces round time from 5 mins to 1 min

Storage:
  - 100 GB SSD
  - Enable fast data reload between rounds

Optional GPU:
  - NVIDIA GeForce RTX 3080 or better
  - Enables XGBoost CUDA acceleration
  - Not needed for MVP correctness
```

---

## 3. Memory Usage Analysis

### 3.1 MVP Memory Footprint

```
Component                          Size      Notes
─────────────────────────────────────────────────────────
1. Dataset (all 10 batches)        ~100 MB   LibSVM sparse format
   - Loaded entirely at startup
   - 13,910 samples × 128 features
   - Sparse storage (not dense matrix)

2. Baseline Model (Gradient Boosting) ~5 MB
   - 100 decision trees
   - ~500 KB per tree
   - Single instance

3. Local Models (10 participants)   ~50 MB   (if keeping in memory)
   - 10 copies of model
   - ~5 MB each
   - Can be discarded after gradient extraction

4. Gradient Tensors (10 participants) ~30 MB
   - One gradient per participant
   - 128 features + metadata
   - Stored temporarily during aggregation

5. Trust Scoring State               ~10 MB
   - Historical trust scores
   - Confidence metrics
   - Gradient history (last 5 rounds)

6. Metadata & Logging               ~5 MB
   - Round logs
   - Participant metadata
   - Audit trail

7. Python Runtime + Libraries        ~200 MB
   - numpy, pandas, scikit-learn
   - matplotlib (for visualization)

─────────────────────────────────────────────────────────
TOTAL PEAK MEMORY:                 ~400 MB   (minimum 8 GB RAM)
TYPICAL WORKING SET:               ~200 MB   (8 GB RAM sufficient)
```

### 3.2 Memory Over Time

```
Startup:
  - Load dataset: 100 MB
  - Initialize libraries: 200 MB
  - Create models: 5 MB
  → Total: ~300 MB

Per Round:
  - Train 10 local models: +50 MB (sequential)
  - Extract gradients: +30 MB
  - Score + aggregate: +10 MB
  → Peak: ~400 MB
  
After Round:
  - Discard local models: -50 MB
  - Keep gradients (5 rounds): +30 MB
  - Keep trust history: +5 MB
  → Steady: ~350 MB
```

### 3.3 Scaling Memory Requirements

| Stage | Participants | Total Samples | Peak Memory | Feasible |
|-------|---|---|---|---|
| MVP (1) | 10 | 13,910 | ~400 MB | ✅ Yes (8 GB) |
| Stage 2 | 20 | 27,820 | ~800 MB | ✅ Yes (8 GB) |
| Stage 3 | 50 | 69,550 | ~2 GB | ✅ Yes (16 GB) |
| Stage 4 | 100 | 139,100 | ~4 GB | ⚠️ 32 GB recommended |
| Stage 5 | 500 | 695,500 | ~20 GB | ❌ Requires distributed |
| Production | 1000+ | 1M+ | 100+ GB | ❌ Requires cloud |

---

## 4. Dataset Scale for MVP

### 4.1 MVP Dataset Configuration

```
Total Samples: 13,910
Split Strategy: File-based partitioning (no random split)

Participant Data:
  - batch1.dat: 445 samples   (3.2% of total)
  - batch2.dat: 1,244 samples (8.9%)
  - batch3.dat: 1,586 samples (11.4%)
  - batch4.dat: 161 samples   (1.2%) ← SMALL
  - batch5.dat: 197 samples   (1.4%) ← SMALL
  - batch6.dat: 2,300 samples (16.5%)
  - batch7.dat: 3,613 samples (26.0%) ← LARGEST
  - batch8.dat: 294 samples   (2.1%)
  - batch9.dat: 470 samples   (3.4%)
  - batch10.dat: 3,600 samples (25.9%)

Feature Space: 128 continuous sparse features
- Index range: 1-128
- Sparsity: 99.78%-99.97%
- No feature scaling/engineering needed

Classes: 6 multiclass labels
- Natural label distribution
- Class imbalance: 1.0× to 106.4×
- Test fairness constraints

Per-Participant Train/Test Split:
  - 80% train data (used for federated updates)
  - 20% test data (validation, trust assessment)
  - Example (batch1 with 445 samples):
    - Train: 356 samples
    - Test: 89 samples
```

### 4.2 Dataset Adequacy for MVP

| Metric | Value | Adequacy |
|--------|-------|----------|
| **Total Samples** | 13,910 | ✅ Sufficient for 10 participants |
| **Min Per-Participant** | 161 | ✅ Adequate (>100 minimum) |
| **Avg Per-Participant** | 1,391 | ✅ Good diversity |
| **Max Per-Participant** | 3,613 | ✅ Tests large-scale gradient stability |
| **Heterogeneity** | 22.4× ratio | ✅ Tests realistic variance |
| **Features** | 128 | ✅ Reasonable complexity |
| **Classes** | 6 | ✅ Non-trivial prediction task |

**Verdict:** ✅ Dataset is appropriately sized for MVP demonstration.

---

## 5. Federated Round Configuration

### 5.1 Round Workflow (MVP)

```python
# MVP Federated Round (Pseudo-code)

def federated_round(round_num, global_model, participants_data):
    """
    Execute one round of federated learning with trust validation.
    
    Args:
        round_num: Current round (1-10)
        global_model: Current Gradient Boosting model
        participants_data: Dict of {org_id: (X_train, y_train, X_test, y_test)}
    
    Returns:
        updated_global_model, trust_decisions, metrics
    """
    
    local_updates = {}
    trust_scores = {}
    confidence_scores = {}
    
    # STEP 1: Broadcast (trivial on single machine)
    for org_id in participants_data.keys():
        send_model(global_model, org_id)  # ~instant
    
    # STEP 2: Local Training (can parallelize in Stage 3)
    for org_id, (X_train, y_train, X_test, y_test) in participants_data.items():
        # Train local model
        local_model = train_local_model(
            global_model.copy(),
            X_train, y_train,
            epochs=1  # Single epoch for federated setting
        )
        
        # Extract gradient/weight update
        gradient = compute_update(global_model, local_model)
        
        local_updates[org_id] = {
            'gradient': gradient,
            'model': local_model,
            'train_size': len(X_train),
            'test_accuracy': local_model.score(X_test, y_test)
        }
    
    # STEP 3: Trust Scoring & Confidence Assessment
    for org_id, update in local_updates.items():
        # Compute 5-dimension trust score
        trust_score = compute_trust_score(
            update['gradient'],
            update['model'],
            participants_data[org_id],
            historical_data  # Previous rounds
        )
        
        # Compute 5-component confidence score
        confidence_score = compute_confidence_score(
            update['gradient'],
            historical_data,
            current_round=round_num
        )
        
        trust_scores[org_id] = trust_score
        confidence_scores[org_id] = confidence_score
        
        # Make decision
        decision = make_decision(trust_score['trust'], trust_score['decision'])
        log_decision(org_id, trust_score, confidence_score, decision)
    
    # STEP 4: Filter by Trust Threshold
    allowed_updates = {
        org_id: update
        for org_id, update in local_updates.items()
        if trust_scores[org_id]['decision'] in ['ALLOW', 'MONITOR']
    }
    
    blocked_updates = {
        org_id: update
        for org_id, update in local_updates.items()
        if trust_scores[org_id]['decision'] in ['REVIEW', 'BLOCK']
    }
    
    # STEP 5: Aggregation (Federated Averaging)
    aggregated_update = federated_average(
        [u['gradient'] for u in allowed_updates.values()],
        weights=[participants_data[org_id][0].shape[0] for org_id in allowed_updates.keys()]
    )
    
    # STEP 6: Apply Update
    updated_global_model = apply_update(global_model, aggregated_update)
    
    # STEP 7: Logging & Metrics
    metrics = {
        'round': round_num,
        'total_participants': len(participants_data),
        'allowed_updates': len(allowed_updates),
        'blocked_updates': len(blocked_updates),
        'allow_rate': len(allowed_updates) / len(participants_data),
        'avg_trust_score': np.mean([t['trust'] for t in trust_scores.values()]),
        'avg_confidence': np.mean([c['confidence'] for c in confidence_scores.values()]),
        'global_model_accuracy': evaluate(updated_global_model),
        'trust_decisions': trust_scores,
        'confidence_scores': confidence_scores
    }
    
    return updated_global_model, metrics
```

### 5.2 Round Timeline (Single Machine, Sequential)

```
Round 1 (start)
├─ T=0ms:      Broadcast model (instant, same machine)
├─ T=1s-30s:   Local training (participant 1)
├─ T=30-60s:   Local training (participant 2)
├─ ...
├─ T=150-180s: Local training (participant 10)
├─ T=180-210s: Gradient extraction (all participants)
├─ T=210-220s: Trust scoring (all participants)
├─ T=220-230s: Confidence assessment
├─ T=230-240s: Aggregation
└─ T=240-250s: Model update

Total: ~5 minutes per round (sequential training)
```

### 5.3 10-Round Execution Timeline

```
Round 1:  T=0min - 5min     (iteration 1/10)
Round 2:  T=5min - 10min    (iteration 2/10)
Round 3:  T=10min - 15min   (iteration 3/10)
Round 4:  T=15min - 20min   (iteration 4/10)
Round 5:  T=20min - 25min   (iteration 5/10)
─────────────────────────── (50 minutes so far)
Round 6:  T=25min - 30min   (iteration 6/10)
Round 7:  T=30min - 35min   (iteration 7/10)
Round 8:  T=35min - 40min   (iteration 8/10)
Round 9:  T=40min - 45min   (iteration 9/10)
Round 10: T=45min - 50min   (iteration 10/10)

Total Execution Time: ~50 minutes
Scenario Injection: Between rounds
Testing: After all rounds complete
```

---

## 6. Controlled Scenario Injection

### 6.1 Scenario Architecture

```python
# 9 Scenarios injected between rounds (not during normal rounds)

SCENARIO_CONFIG = {
    1: {
        'name': 'Clean Baseline',
        'participants': ['org_1', 'org_2', ..., 'org_10'],
        'modification': None,
        'expected_trust': 90,
        'expected_decision': 'ALLOW',
        'validation': lambda t: t > 85
    },
    2: {
        'name': 'Label Noise 5%',
        'participants': ['org_2'],  # Only affect org_2
        'modification': corrupt_labels(y, p=0.05),
        'expected_trust': 80,
        'expected_decision': 'MONITOR',
        'validation': lambda t: 70 < t < 90
    },
    3: {
        'name': 'Label Noise 50%',
        'participants': ['org_3'],
        'modification': corrupt_labels(y, p=0.50),
        'expected_trust': 30,
        'expected_decision': 'BLOCK',
        'validation': lambda t: t < 40
    },
    # ... 6 more scenarios
}

# Execution model
for scenario_num, config in SCENARIO_CONFIG.items():
    print(f"Injecting Scenario {scenario_num}: {config['name']}")
    
    # Modify selected participants' data
    modified_data = apply_scenario(config)
    
    # Run single trust evaluation round
    results = evaluate_scenario(
        modified_data,
        global_model,
        scenario_num
    )
    
    # Validate results match expectations
    assert config['validation'](results['trust_score']), \
        f"Scenario {scenario_num} failed validation"
    
    print(f"  ✓ PASSED (trust={results['trust_score']}, "
          f"decision={results['decision']})")
```

### 6.2 Scenario Execution Timeline

```
Main Training: Rounds 1-5 (normal federated learning)
    └─ T=0-25min

Scenario Injection: Between round 5 and 6
    ├─ Scenario 1 (Clean): T=25-26min
    ├─ Scenario 2 (Noise 5%): T=26-27min
    ├─ Scenario 3 (Noise 50%): T=27-28min
    ├─ Scenario 4 (Poisoned): T=28-29min
    ├─ Scenario 5 (Drift): T=29-30min
    ├─ Scenario 6 (Stale): T=30-31min
    ├─ Scenario 7 (Imbalance): T=31-32min
    ├─ Scenario 8 (Byzantine): T=32-33min
    └─ Scenario 9 (Variance): T=33-34min

Validation Testing: T=34-50min
    └─ Verify all scenarios completed correctly
```

---

## 7. MVP Limitations

### 7.1 Explicit Limitations (By Design)

#### Communication Model
```
❌ LIMITATION: Synchronous, blocking communication
✅ WHY: Simplifies implementation, no async/event handling needed
✅ ACCEPTABLE: Single machine, no network latency

❌ LIMITATION: No Byzantine-robust aggregation
✅ WHY: MVP validates trust scoring (aggregation is basic averaging)
✅ PLAN: Stage 3+ adds robust aggregation

❌ LIMITATION: No horizontal scalability
✅ WHY: Single Python process, single thread(s)
✅ PLAN: Stage 3+ uses multiprocessing, Stage 4+ uses distributed systems
```

#### Trust Scoring
```
❌ LIMITATION: Trust scores computed on-the-fly (no caching)
✅ WHY: Demonstrates correctness, not performance optimization
✅ ACCEPTABLE: 10 participants, fast enough

❌ LIMITATION: No incremental gradient computation
✅ WHY: Full recomputation acceptable for MVP
✅ PLAN: Stage 2+ optimizes with incremental updates
```

#### Participant Management
```
❌ LIMITATION: All participants must be available for every round
✅ WHY: No dropout/fault tolerance mechanism needed for MVP
✅ PLAN: Stage 2+ adds participant resilience

❌ LIMITATION: Static participant set (no add/remove mid-training)
✅ WHY: Simplifies round coordination
✅ PLAN: Stage 3+ supports dynamic participant addition
```

#### Model & Data
```
❌ LIMITATION: Single baseline model type (Gradient Boosting only)
✅ WHY: Demonstrates trust scoring on one model type
✅ PLAN: Stage 2+ adds neural networks, other models

❌ LIMITATION: Fixed dataset (13,910 samples, 128 features)
✅ WHY: No data ingestion pipeline needed
✅ PLAN: Stage 3+ integrates live data sources

❌ LIMITATION: No feature engineering or preprocessing
✅ WHY: Uses data as-is from batch files
✅ PLAN: Stage 2+ adds configurable preprocessing
```

#### Storage & Persistence
```
❌ LIMITATION: No persistent storage (everything in-memory)
✅ WHY: MVP runs end-to-end without restart
✅ PLAN: Stage 2+ adds SQLite logging, Stage 3+ uses databases

❌ LIMITATION: No checkpointing or recovery
✅ WHY: If crashed, start from scratch (acceptable for demo)
✅ PLAN: Stage 2+ adds round-level checkpoints
```

### 7.2 Performance Limitations

```
Metric                     MVP Limit      Stage 3 Target   Stage 5 Target
────────────────────────────────────────────────────────────────────────
Max Participants           10             50               500+
Max Rounds                 10             50               1000+
Total Dataset Size         13.9 KB        1 MB             1 GB
Round Time (Sequential)    5 min          2 min            <1 sec
Throughput (samples/sec)   47             500              10,000+
Memory Peak                400 MB         2 GB             100 GB+
Storage Needed             50 GB          200 GB           10 TB+
```

### 7.3 What MVP Does NOT Include

```
❌ Model versioning / checkpointing
❌ Automatic model persistence
❌ Audit trail with signatures
❌ Data encryption (in transit or at rest)
❌ Differential privacy
❌ Secure multi-party computation
❌ Hardware security modules
❌ Regulatory compliance (HIPAA, GDPR)
❌ High availability (HA)
❌ Disaster recovery (DR)
❌ Load balancing
❌ Real-time streaming data
❌ Multi-model ensemble
❌ Hyperparameter optimization
❌ AutoML capabilities
❌ Explainability/interpretability
❌ A/B testing framework
❌ Monitoring/alerting systems
❌ Rollback capabilities
```

---

## 8. What Works in MVP vs. Production

### 8.1 Trust Scoring System

#### ✅ WORKS IN MVP
- **5-Dimensional Trust Score** with formulas from TRUST_MODEL.md
- **5-Component Confidence Score** with formulas from CONFIDENCE_MODEL.md
- **Decision Logic** (ALLOW/MONITOR/REVIEW/BLOCK)
- **Mathematical Correctness** (all formulas correctly implemented)
- **Scenario Validation** (9 scenarios produce expected outcomes)
- **End-to-End Validation** from gradient to decision

#### ❌ NOT IN MVP (Production Only)
- **Real-time Trust Scoring** (MVP computes offline between rounds)
- **Incremental Updates** (MVP recomputes from scratch)
- **Distributed Scoring** (MVP runs on single machine)
- **Continuous Monitoring** (MVP scores only at round boundaries)
- **Complex Gradient Forensics** (MVP uses basic gradient comparison)
- **ML-based Anomaly Detection** (MVP uses rule-based detection)
- **Feedback Loop Learning** (MVP uses static thresholds)

### 8.2 Federated Learning Framework

#### ✅ WORKS IN MVP
- **Local Model Training** at each participant
- **Gradient Extraction** from trained models
- **Federated Averaging** of gradients
- **Model Update** aggregation
- **Multiple Rounds** (1-10) with model improvement
- **Heterogeneous Participants** (different data distributions)
- **Controlled Experiments** (scenario injection)

#### ❌ NOT IN MVP (Production Only)
- **Participant Dropout Tolerance** (all must participate each round)
- **Asynchronous Updates** (MVP is fully synchronous)
- **Gradient Compression** (MVP uses full-precision gradients)
- **Secure Aggregation** (MVP uses unencrypted averaging)
- **Communication Efficiency** (MVP transfers full models)
- **Bandwidth Optimization** (MVP not optimized)
- **Participant Anonymity** (MVP tracks all participants)

### 8.3 Data Handling

#### ✅ WORKS IN MVP
- **LibSVM Format Parsing** (correct sparse format handling)
- **File-based Partitioning** (10 participants from batch files)
- **Train/Test Splitting** (80/20 per participant)
- **Data Quality Checks** (missing values, outliers)
- **Class Distribution Handling** (natural imbalance)
- **Feature Standardization** (data as-is from files)

#### ❌ NOT IN MVP (Production Only)
- **Live Data Streaming** (MVP uses static batch files)
- **Dynamic Schema Evolution** (MVP fixed schema)
- **Data Versioning** (MVP no version tracking)
- **Lineage Tracking** (MVP no data provenance)
- **PII Detection/Removal** (MVP no privacy checks)
- **Data Anonymization** (MVP raw data)
- **Compliance Validation** (MVP no regulatory checks)

### 8.4 System Architecture

#### ✅ WORKS IN MVP
- **Single Coordinator** (one Python process)
- **10 Simulated Participants** (in-memory)
- **Synchronous Communication** (function calls)
- **Memory-based Storage** (no persistence)
- **Deterministic Execution** (same seed = same results)
- **Comprehensive Logging** (text output)

#### ❌ NOT IN MVP (Production Only)
- **Distributed Architecture** (MVP single machine)
- **Thousands of Participants** (MVP only 10)
- **Asynchronous Messaging** (MVP synchronous)
- **Persistent Storage** (MVP in-memory only)
- **Fault Tolerance** (MVP no recovery)
- **High Availability** (MVP single point of failure)
- **Monitoring Systems** (MVP manual observation)

---

## 9. Summary: MVP Scope Box

### The Box: What's Included

```
┌─────────────────────────────────────────────────────────┐
│  PROTECTOR UTTAM MVP PROTOTYPE                          │
│                                                          │
│  ✅ 10 Simulated Participants (file-based)              │
│  ✅ 5-10 Federated Rounds (complete training cycle)    │
│  ✅ 13,910 Training Samples (existing dataset)         │
│  ✅ 128-Feature Classification (6 classes)             │
│  ✅ Trust Scoring (5 dimensions proven correct)        │
│  ✅ Confidence Assessment (5 components validated)    │
│  ✅ Decision Logic (ALLOW/MONITOR/REVIEW/BLOCK)       │
│  ✅ 9 Controlled Scenarios (injected validation)       │
│  ✅ Single Machine Deployment (400 MB RAM peak)        │
│  ✅ ~50 Minute Runtime (end-to-end execution)         │
│                                                          │
│  🎯 PURPOSE: Demonstrate trust scoring correctness     │
│  🎯 USERS: Development team, stakeholders              │
│  🎯 PLATFORM: Laptop/workstation with 8 GB RAM        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Outside the Box: What's NOT Included

```
❌ Production scalability (millions of participants)
❌ Distributed infrastructure (Cloud, K8s, etc.)
❌ Real-time processing (streaming data)
❌ High availability (no fault tolerance)
❌ Persistent storage (no databases)
❌ Security hardening (encryption, signing)
❌ Compliance features (HIPAA, GDPR, SOX)
❌ Monitoring & alerting (ops visibility)
❌ Advanced models (neural networks)
❌ Real data pipelines (data ingestion)
```

---

## 10. MVP Success Criteria

The prototype is successful if it demonstrates:

- [ ] **Trust Score Correctness:** All 5 dimensions compute correctly per formulas
- [ ] **Confidence Score Validation:** All 5 components follow specification
- [ ] **Decision Logic:** ALLOW/MONITOR/REVIEW/BLOCK thresholds respected
- [ ] **Scenario Accuracy:** 9 scenarios produce expected trust outcomes
- [ ] **Federated Learning:** Models improve over rounds 1-5
- [ ] **Heterogeneity Handling:** Participants with 1:22 sample ratios work correctly
- [ ] **Performance:** Complete 10 rounds in <1 hour on 8GB RAM machine
- [ ] **Reproducibility:** Same results with same random seed
- [ ] **Documentation:** All decisions explained in logs/reports
- [ ] **Code Quality:** Well-documented, no crashes on edge cases

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024 | Team | Initial MVP scope definition |

**End of Prototype Scale Definition**
