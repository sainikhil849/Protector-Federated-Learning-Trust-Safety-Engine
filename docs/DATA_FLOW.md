# Data Flow
## Protector Uttam: Data Pipeline Architecture

**Document Type:** Data Processing Reference  
**Version:** 1.0  
**Date:** 2024  
**Diagrams:** 4 detailed data flow views  

---

## 1. Dataset Flow: Raw to Distributed

Complete flow from raw dataset files through preprocessing to participant distribution:

```mermaid
graph LR
    subgraph SOURCE["📁 SOURCE DATASET"]
        B1["batch1.dat<br/>(1,391 samples)"]
        B2["batch2.dat<br/>(1,391 samples)"]
        B3["batch3.dat<br/>(1,391 samples)"]
        B4["..."]
        B10["batch10.dat<br/>(1,391 samples)"]
        TOTAL["Total: 13,910 samples<br/>128 features<br/>6 classes"]
    end
    
    subgraph PARSE["📖 PARSING STAGE"]
        LIBSVM["LibSVM Format Parser<br/>[label] [idx]:[val] ..."]
        VALIDATE["Format Validation<br/>(Features 1-128)"]
        EXTRACT["Feature Extraction<br/>(Sparse vectors)"]
    end
    
    subgraph CLEAN["🧹 CLEANING STAGE"]
        OUTLIER["Outlier Detection<br/>(Bounds checking)"]
        SCHEMA["Schema Validation<br/>(Type checking)"]
        COMPLETE["Completeness Check<br/>(Non-null)"]
    end
    
    subgraph PARTITION["👥 PARTICIPANT PARTITIONING"]
        MAP["Org ID Mapping<br/>(batch → org)"]
        SPLIT["Data Split:<br/>Org_1 → batch1.dat<br/>Org_2 → batch2.dat<br/>...<br/>Org_10 → batch10.dat"]
        ASSIGN["Assignment"]
    end
    
    subgraph DIST["📤 DISTRIBUTION"]
        LOAD["Load into Memory<br/>(In-RAM)"]
        TRAIN_TEST["Train/Test Split<br/>(80/20)"]
        READY["Ready for Training"]
    end
    
    B1 --> LIBSVM
    B2 --> LIBSVM
    B3 --> LIBSVM
    B10 --> LIBSVM
    
    LIBSVM --> VALIDATE
    VALIDATE --> EXTRACT
    
    EXTRACT --> OUTLIER
    OUTLIER --> SCHEMA
    SCHEMA --> COMPLETE
    
    COMPLETE --> MAP
    MAP --> SPLIT
    SPLIT --> ASSIGN
    
    ASSIGN --> LOAD
    LOAD --> TRAIN_TEST
    TRAIN_TEST --> READY
    
    style SOURCE fill:#e3f2fd
    style PARSE fill:#f3e5f5
    style CLEAN fill:#e8f5e9
    style PARTITION fill:#fff3e0
    style DIST fill:#e0f2f1
```

---

## 2. Federated Training Flow

Complete flow of local training at each participant, from data to gradient extraction:

```mermaid
graph TD
    subgraph ROUND["🔄 FEDERATED ROUND START"]
        GLOBAL["Global Model<br/>(t-1)"]
        BROADCAST["Broadcast to<br/>10 Participants"]
    end
    
    subgraph PARTICIPANT["👤 PARTICIPANT (Per Org)"]
        RECEIVE["Receive<br/>Global Model"]
        LOCAL_DATA["Local Dataset<br/>(e.g., 1,391 samples)"]
        SPLIT["Split into<br/>Train/Test<br/>(80/20)"]
        
        TRAIN["Local Training<br/>(Gradient Boosting)"]
        EVALUATE["Local Evaluation<br/>(Compute metrics)"]
        LOCAL_ACC["Local Accuracy"]
    end
    
    subgraph GRADIENT["📊 GRADIENT EXTRACTION"]
        EXTRACT["Extract Update<br/>(∂ loss/∂ weights)"]
        COMPUTE["Compute Delta<br/>(new_weights - old_weights)"]
        MAGNITUDE["Magnitude Check<br/>(||∆w||)"]
    end
    
    subgraph INTEGRITY["🔐 INTEGRITY CHECK"]
        HASH["SHA256 Hash<br/>(Gradient)"]
        SIGN["Signature<br/>(Optional in MVP)"]
        PACKAGE["Package Update<br/>(Hash + Delta)"]
    end
    
    subgraph READY["✅ UPDATE READY"]
        UPDATE["Complete Local Update<br/>(Ready for next stage)"]
    end
    
    GLOBAL --> BROADCAST
    BROADCAST --> RECEIVE
    RECEIVE --> TRAIN
    LOCAL_DATA --> SPLIT
    SPLIT --> TRAIN
    TRAIN --> EVALUATE
    EVALUATE --> LOCAL_ACC
    
    LOCAL_ACC --> EXTRACT
    EXTRACT --> COMPUTE
    COMPUTE --> MAGNITUDE
    MAGNITUDE --> HASH
    HASH --> SIGN
    SIGN --> PACKAGE
    PACKAGE --> UPDATE
    
    style ROUND fill:#fff3e0
    style PARTICIPANT fill:#e8f5e9
    style GRADIENT fill:#f3e5f5
    style INTEGRITY fill:#ffebee
    style READY fill:#c8e6c9
```

---

## 3. Detailed Update Flow: From Participant to Decision

Complete flow of a single participant's update through all validation stages:

```mermaid
graph TD
    subgraph INPUT["📥 UPDATE RECEIPT"]
        ORG["Organization ID"]
        GRAD["Gradient Vector<br/>(128-dim)"]
        HASH["Hash"]
        TIMESTAMP["Timestamp"]
        LOCAL_METRIC["Local Metrics<br/>(accuracy, loss, etc.)"]
    end
    
    subgraph HARD_GATE["🛡️ HARD SAFETY GATE"]
        STRUCT["Structural Validation"]
        STRUCT1["✓ Gradient shape valid"]
        STRUCT2["✓ All features present"]
        STRUCT3["✓ No NaN/Inf values"]
        
        BOUNDS["Magnitude Bounds"]
        BOUNDS1["✓ ||∆w|| < 1000 (tuned)"]
        BOUNDS2["✓ No extreme values"]
        
        FRESH["Freshness Check"]
        FRESH1["✓ Timestamp recent"]
        FRESH2["✓ No duplicates"]
        
        GATE_DECISION{{"Hard Gate<br/>Decision"}}
    end
    
    subgraph SOFT_GATES["📊 SOFT SCORING (If Gate Pass)"]
        DQS["DQS Engine"]
        DQS_CALC["Data Quality Score"]
        
        DHS["DHS Engine"]
        DHS_CALC["Drift Health Score"]
        
        USS["USS Engine"]
        USS_CALC["Update Safety Score"]
        
        RS["RS Engine"]
        RS_CALC["Reliability Score"]
        
        PS["PS Engine"]
        PS_CALC["Performance Score"]
    end
    
    subgraph TRUST["🎯 TRUST CALCULATION"]
        WEIGHTS["Apply Weights<br/>(25%, 25%, 20%, 20%, 10%)"]
        FORMULA["TRUST = 0.25×DQS + 0.25×DHS<br/>+ 0.20×USS + 0.20×RS + 0.10×PS"]
        SCORE["Trust Score<br/>(0-100)"]
    end
    
    subgraph CONF["🎲 CONFIDENCE ASSESSMENT"]
        CONF_CALC["Calculate Confidence<br/>(5 components)"]
        CONF_SCORE["Confidence Level<br/>(HIGH/MEDIUM/LOW/INSUFFICIENT)"]
    end
    
    subgraph DECISION["🚦 DECISION ENGINE"]
        THRESHOLD["Apply Thresholds"]
        CHECK1["TRUST ≥ 75 → ALLOW"]
        CHECK2["60 ≤ TRUST < 75 → MONITOR"]
        CHECK3["40 ≤ TRUST < 60 → REVIEW"]
        CHECK4["TRUST < 40 → BLOCK"]
        FINAL_DECISION["Final Decision<br/>(ALLOW/MONITOR/REVIEW/BLOCK)"]
    end
    
    subgraph FALLBACK["⚠️ FALLBACK PATHS"]
        ALLOW["ALLOW:<br/>Use in aggregation"]
        MONITOR["MONITOR:<br/>Track closely,<br/>still use"]
        REVIEW["REVIEW:<br/>Manual review<br/>before use"]
        BLOCK["BLOCK:<br/>Do not use,<br/>isolate participant"]
    end
    
    ORG --> STRUCT
    GRAD --> STRUCT
    HASH --> BOUNDS
    TIMESTAMP --> FRESH
    LOCAL_METRIC --> DQS
    
    STRUCT --> STRUCT1
    STRUCT --> STRUCT2
    STRUCT --> STRUCT3
    STRUCT1 --> GATE_DECISION
    STRUCT2 --> GATE_DECISION
    STRUCT3 --> GATE_DECISION
    
    BOUNDS --> BOUNDS1
    BOUNDS --> BOUNDS2
    BOUNDS1 --> GATE_DECISION
    BOUNDS2 --> GATE_DECISION
    
    FRESH --> FRESH1
    FRESH --> FRESH2
    FRESH1 --> GATE_DECISION
    FRESH2 --> GATE_DECISION
    
    GATE_DECISION -->|PASS| DQS
    GATE_DECISION -->|FAIL| REJECT["❌ REJECT:<br/>Critical safety issue"]
    
    DQS --> DQS_CALC
    DHS --> DHS_CALC
    USS --> USS_CALC
    RS --> RS_CALC
    PS --> PS_CALC
    
    DQS_CALC --> WEIGHTS
    DHS_CALC --> WEIGHTS
    USS_CALC --> WEIGHTS
    RS_CALC --> WEIGHTS
    PS_CALC --> WEIGHTS
    
    WEIGHTS --> FORMULA
    FORMULA --> SCORE
    SCORE --> CONF_CALC
    CONF_CALC --> CONF_SCORE
    
    CONF_SCORE --> THRESHOLD
    SCORE --> THRESHOLD
    
    THRESHOLD --> CHECK1
    THRESHOLD --> CHECK2
    THRESHOLD --> CHECK3
    THRESHOLD --> CHECK4
    
    CHECK1 --> FINAL_DECISION
    CHECK2 --> FINAL_DECISION
    CHECK3 --> FINAL_DECISION
    CHECK4 --> FINAL_DECISION
    
    FINAL_DECISION --> ALLOW
    FINAL_DECISION --> MONITOR
    FINAL_DECISION --> REVIEW
    FINAL_DECISION --> BLOCK
    
    style INPUT fill:#e3f2fd
    style HARD_GATE fill:#ffebee
    style SOFT_GATES fill:#e8f5e9
    style TRUST fill:#fff3e0
    style CONF fill:#f3e5f5
    style DECISION fill:#f1f8e9
    style FALLBACK fill:#ffd43b
    style REJECT fill:#ff6b6b
```

---

## 4. Aggregation & Update Flow

Flow from accepted updates through aggregation to global model update:

```mermaid
graph TD
    subgraph COLLECT["📦 COLLECT DECISIONS"]
        ALLOW_SET["Updates with ALLOW<br/>(Trust ≥ 75)"]
        MONITOR_SET["Updates with MONITOR<br/>(60 ≤ Trust < 75)"]
        REVIEW_SET["Updates with REVIEW<br/>(40 ≤ Trust < 60)"]
        BLOCK_SET["Updates with BLOCK<br/>(Trust < 40)"]
        
        STATISTICS["Statistics:<br/>- ALLOW count<br/>- MONITOR count<br/>- BLOCK count"]
    end
    
    subgraph FILTER["🎯 FILTER POLICY"]
        POLICY["Aggregation Policy:<br/>Default: Use ALLOW only<br/>Alternative: ALLOW + MONITOR"]
        FILTERED["Filtered Set<br/>(Selected updates only)"]
    end
    
    subgraph AGGREGATE["∑ FEDERATED AVERAGING"]
        GRADIENTS["Extract Gradients<br/>from Filtered Set"]
        STACK["Stack into Matrix<br/>(K × 128 features)"]
        AVERAGE["Compute Mean<br/>per feature"]
        AGG_GRADIENT["Aggregated Gradient<br/>(Average of all)"]
    end
    
    subgraph CLIP["✂️ OPTIONAL GRADIENT CLIPPING"]
        MAGNITUDE_CHECK["Check Magnitude<br/>||∆w_agg||"]
        CLIP_CHECK["Is magnitude<br/>too large?"]
        CLIPPED["Clip if needed<br/>(Safety margin)"]
    end
    
    subgraph UPDATE["🔄 APPLY UPDATE"]
        LEARNING_RATE["Apply Learning Rate<br/>(α)"]
        NEW_WEIGHTS["new_w = w - α × ∆w_agg"]
        MODEL_UPDATE["Global Model<br/>Updated"]
    end
    
    subgraph VALIDATE_UPDATE["✅ VALIDATE GLOBAL MODEL"]
        SANITY["Sanity Check<br/>(Weights in valid range)"]
        EVALUATE["Evaluate on Global<br/>Validation Set"]
        GLOBAL_ACCURACY["New Global Accuracy"]
    end
    
    subgraph CHECKPOINT["💾 CHECKPOINT"]
        SAVE_MODEL["Save Model<br/>Version (t)"]
        SAVE_STATE["Save State<br/>(Round number)"]
        SAVE_METRICS["Save Metrics<br/>(Accuracy, loss)"]
    end
    
    subgraph NEXT["🔄 NEXT ROUND"]
        BROADCAST_NEXT["Broadcast Model<br/>to Participants (t+1)"]
        READY_NEXT["Ready for<br/>Next Round"]
    end
    
    ALLOW_SET --> STATISTICS
    MONITOR_SET --> STATISTICS
    REVIEW_SET --> STATISTICS
    BLOCK_SET --> STATISTICS
    
    STATISTICS --> POLICY
    POLICY --> FILTERED
    
    FILTERED --> GRADIENTS
    GRADIENTS --> STACK
    STACK --> AVERAGE
    AVERAGE --> AGG_GRADIENT
    
    AGG_GRADIENT --> MAGNITUDE_CHECK
    MAGNITUDE_CHECK --> CLIP_CHECK
    CLIP_CHECK -->|Yes| CLIPPED
    CLIP_CHECK -->|No| LEARNING_RATE
    CLIPPED --> LEARNING_RATE
    
    LEARNING_RATE --> NEW_WEIGHTS
    NEW_WEIGHTS --> MODEL_UPDATE
    
    MODEL_UPDATE --> SANITY
    SANITY --> EVALUATE
    EVALUATE --> GLOBAL_ACCURACY
    
    GLOBAL_ACCURACY --> SAVE_MODEL
    SAVE_MODEL --> SAVE_STATE
    SAVE_STATE --> SAVE_METRICS
    
    SAVE_METRICS --> BROADCAST_NEXT
    BROADCAST_NEXT --> READY_NEXT
    
    READY_NEXT -.->|Next Round| COLLECT
    
    style COLLECT fill:#e3f2fd
    style FILTER fill:#f3e5f5
    style AGGREGATE fill:#e0f2f1
    style CLIP fill:#ffebee
    style UPDATE fill:#e8f5e9
    style VALIDATE_UPDATE fill:#fff3e0
    style CHECKPOINT fill:#f1f8e9
    style NEXT fill:#c8e6c9
```

---

## Data Format Specification

### LibSVM Format

Each line in dataset files (batch1.dat through batch10.dat):

```
[label] [feature_index]:[feature_value] [feature_index]:[feature_value] ...

Examples:
1 1:0.5 10:1.2 50:0.1 128:99.5
3 5:1.0 20:2.1 40:0.5
2 1:0.1 50:0.2 100:1.5 128:50.0
```

### Properties

```
Label Space:        {1, 2, 3, 4, 5, 6} (6-class multiclass)
Feature Space:      {1, 2, ..., 128}
Feature Values:     Continuous [0.1, 170000+]
Sparsity:           99.78%-99.97% (very sparse)
Total Samples:      13,910
Samples per File:   ~1,391
Features per Line:  1-40 features typically (out of 128)
```

---

## Participant Data Distribution

```
Participant Mapping:
┌──────────────────────────┬─────────────┬────────────┐
│ Organization ID          │ Batch File  │ Samples    │
├──────────────────────────┼─────────────┼────────────┤
│ Org_1                    │ batch1.dat  │ 1,391      │
│ Org_2                    │ batch2.dat  │ 1,391      │
│ Org_3                    │ batch3.dat  │ 1,391      │
│ Org_4                    │ batch4.dat  │ 1,391      │
│ Org_5                    │ batch5.dat  │ 1,391      │
│ Org_6                    │ batch6.dat  │ 1,391      │
│ Org_7                    │ batch7.dat  │ 1,391      │
│ Org_8                    │ batch8.dat  │ 1,391      │
│ Org_9                    │ batch9.dat  │ 1,391      │
│ Org_10                   │ batch10.dat │ 1,391      │
├──────────────────────────┼─────────────┼────────────┤
│ TOTAL                    │             │ 13,910     │
└──────────────────────────┴─────────────┴────────────┘
```

---

## Key Constraints

### Data Volume Constraints

```
Memory Usage per Round:
- Dataset loaded: 100 MB
- Per-participant models: ~10 MB each × 10 = 100 MB
- Gradient storage: ~1 MB each × 10 = 10 MB
- Global model: 10 MB
- Working memory: 180 MB

Total Peak: ~400 MB (well under 8 GB MVP requirement)
```

### Processing Order

1. **Sequential (MVP):** Participants trained one at a time (5 min/round)
2. **Parallel (Stage 3):** 4-8 participants in parallel (2 min/round)
3. **Async (Stage 4):** Participants respond when ready (30 sec target)

### Data Quality Expectations

```
Expected Properties:
- No missing values (sparse features naturally absent)
- Bounded values (checked by hard safety gate)
- Class distribution: Natural imbalance (feature not bug)
- Feature distribution: Sparse and bounded
- Outlier rate: <1% (detected and reported)
```

---

## Document History

| Version | Date | Author | Notes |
|---------|------|--------|-------|
| 1.0 | 2024 | Team | Initial data flow architecture |

**End of Data Flow**
