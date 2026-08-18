# Decision Flow
## Protector Uttam: Trust, Confidence & Decision Architecture

**Document Type:** Scoring & Decision Logic Reference  
**Version:** 1.0  
**Date:** 2024  
**Diagrams:** 7 detailed decision flow views  

---

## 1. Hard Safety Gate: Structural Validation

First line of defense - filters out structurally invalid updates:

```mermaid
graph TD
    subgraph INPUT["📥 UPDATE RECEIVED"]
        GRAD["Gradient Vector"]
        META["Metadata:<br/>Org ID, Timestamp,<br/>Hash, Local Metrics"]
    end
    
    subgraph CHECKS["🔍 HARD SAFETY CHECKS"]
        CHECK1["Structural<br/>Validation"]
        C1A["Gradient shape<br/>matches 128 dims?"]
        C1B["All required fields<br/>present?"]
        C1C["No NaN or Inf<br/>values?"]
        
        CHECK2["Magnitude<br/>Bounds"]
        C2A["Gradient magnitude<br/>≤ 1000?"]
        C2B["Magnitude > 0?<br/>(not zero)"]
        C2C["No extreme<br/>outliers?"]
        
        CHECK3["Freshness<br/>Check"]
        C3A["Timestamp within<br/>last 60s?"]
        C3B["Not duplicate<br/>of previous?"]
        C3C["Hash matches<br/>computed?"]
        
        CHECK4["Completeness"]
        C4A["All metadata<br/>fields populated?"]
        C4B["Org ID valid<br/>(1-10)?"]
    end
    
    subgraph DECISION["⚖️ GATE DECISION"]
        ALL_PASS{"All Checks<br/>Pass?"}
        PASS["✅ PASS<br/>Proceed to Soft Scoring"]
        FAIL["❌ FAIL<br/>Reject Update"]
    end
    
    subgraph RESPONSE["📤 RESPONSE"]
        LOG["Log Failure<br/>Reason"]
        ISOLATE["Isolate Participant<br/>(Optional)"]
        SKIP["Skip to Next<br/>Participant"]
    end
    
    GRAD --> CHECK1
    META --> CHECK2
    META --> CHECK3
    META --> CHECK4
    
    CHECK1 --> C1A
    CHECK1 --> C1B
    CHECK1 --> C1C
    CHECK2 --> C2A
    CHECK2 --> C2B
    CHECK2 --> C2C
    CHECK3 --> C3A
    CHECK3 --> C3B
    CHECK3 --> C3C
    CHECK4 --> C4A
    CHECK4 --> C4B
    
    C1A --> ALL_PASS
    C1B --> ALL_PASS
    C1C --> ALL_PASS
    C2A --> ALL_PASS
    C2B --> ALL_PASS
    C2C --> ALL_PASS
    C3A --> ALL_PASS
    C3B --> ALL_PASS
    C3C --> ALL_PASS
    C4A --> ALL_PASS
    C4B --> ALL_PASS
    
    ALL_PASS -->|Yes| PASS
    ALL_PASS -->|No| FAIL
    
    PASS --> CONTINUE["Continue to<br/>Soft Scoring"]
    FAIL --> LOG
    LOG --> ISOLATE
    ISOLATE --> SKIP
    
    style INPUT fill:#e3f2fd
    style CHECKS fill:#ffebee
    style DECISION fill:#fff3e0
    style RESPONSE fill:#f1f8e9
    style PASS fill:#c8e6c9
    style FAIL fill:#ff6b6b
```

---

## 2. Trust Score Calculation: Five Dimensions

Detailed calculation of the 5-component trust score:

```mermaid
graph TB
    subgraph ENGINE1["🏢 DATA QUALITY SCORE (DQS) - 25% Weight"]
        DQ_INPUT["Input: Raw data<br/>from participant"]
        
        DQS1["Schema Validation"]
        DQS1A["✓ All 128 features<br/>in valid range"]
        DQS1B["✓ Label in {1,2,3,4,5,6}"]
        DQS1C["✓ No NaN, Inf, null"]
        
        DQS2["Completeness Check"]
        DQS2A["✓ Non-empty dataset"]
        DQS2B["✓ Consistent format"]
        
        DQS3["Outlier Detection"]
        DQS3A["Outlier rate"]
        DQS3B["Score -= (outlier_pct)"]
        
        DQS_SCORE["DQS Result<br/>(0-100)"]
    end
    
    subgraph ENGINE2["📊 DRIFT HEALTH SCORE (DHS) - 25% Weight"]
        DH_INPUT["Input: Feature<br/>distributions"]
        
        DHS1["Population Stability<br/>Index (PSI)"]
        DHS1A["Compare participant<br/>distribution to"]
        DHS1B["global distribution"]
        
        DHS2["Calculate PSI"]
        DHS2A["PSI = Σ (exp_pct - obs_pct)<br/>× ln(exp_pct/obs_pct)"]
        DHS2B["Per feature"]
        
        DHS3["PSI Thresholds"]
        DHS3A["PSI < 0.1 → No drift<br/>Score = 100"]
        DHS3B["0.1 ≤ PSI < 0.25 → Minor<br/>Score = 80"]
        DHS3C["PSI ≥ 0.25 → Major<br/>Score = 40"]
        
        DHS_SCORE["DHS Result<br/>(0-100)"]
    end
    
    subgraph ENGINE3["🔄 UPDATE SAFETY SCORE (USS) - 20% Weight"]
        US_INPUT["Input: Gradient<br/>vector"]
        
        USS1["Gradient Validity"]
        USS1A["All values finite"]
        USS1B["Magnitude reasonable"]
        USS1C["No infinite loops in<br/>training"]
        
        USS2["Magnitude Analysis"]
        USS2A["||∆w|| in (0, 1000]"]
        USS2B["Not zero gradient"]
        USS2C["Not explosion"]
        
        USS3["Freshness"]
        USS3A["Gradient < 60s old"]
        USS3B["Recent round number"]
        
        USS_SCORE["USS Result<br/>(0-100)"]
    end
    
    subgraph ENGINE4["💓 RELIABILITY SCORE (RS) - 20% Weight"]
        RE_INPUT["Input: Participant<br/>history"]
        
        RS1["Availability"]
        RS1A["Heartbeat recent<br/>(last 5 rounds)"]
        RS1B["Success rate > 90%"]
        
        RS2["Consistency"]
        RS2A["No missed rounds<br/>recently"]
        RS2B["Updates on schedule"]
        
        RS3["Stability"]
        RS3A["Metric variance<br/>acceptable"]
        RS3B["No erratic behavior"]
        
        RS_SCORE["RS Result<br/>(0-100)"]
    end
    
    subgraph ENGINE5["🎯 PERFORMANCE SCORE (PS) - 10% Weight"]
        PE_INPUT["Input: Model<br/>performance"]
        
        PS1["Accuracy Check"]
        PS1A["Local accuracy<br/>≥ baseline"]
        PS1B["Not degrading"]
        
        PS2["Fairness Metrics"]
        PS2A["Per-class performance<br/>balanced"]
        PS2B["No class collapse"]
        
        PS3["Model Delta"]
        PS3A["Model improvement<br/>or stable"]
        PS3B["Not catastrophic<br/>degradation"]
        
        PS_SCORE["PS Result<br/>(0-100)"]
    end
    
    subgraph COMBINE["📊 COMBINE ALL SCORES"]
        FORMULA["TRUST = <br/>0.25×DQS +<br/>0.25×DHS +<br/>0.20×USS +<br/>0.20×RS +<br/>0.10×PS"]
        FINAL["Final Trust Score<br/>(0-100)"]
    end
    
    DQ_INPUT --> DQS1
    DQS1 --> DQS1A
    DQS1 --> DQS1B
    DQS1 --> DQS1C
    DQS1A --> DQS_SCORE
    DQS1B --> DQS_SCORE
    DQS1C --> DQS_SCORE
    DQS2 --> DQS_SCORE
    DQS3 --> DQS_SCORE
    
    DH_INPUT --> DHS1
    DHS1 --> DHS1A
    DHS1 --> DHS1B
    DHS1A --> DHS2
    DHS1B --> DHS2
    DHS2 --> DHS2A
    DHS2A --> DHS3
    DHS3 --> DHS3A
    DHS3 --> DHS3B
    DHS3 --> DHS3C
    DHS3A --> DHS_SCORE
    
    US_INPUT --> USS1
    USS1 --> USS1A
    USS2 --> USS_SCORE
    USS3 --> USS_SCORE
    
    RE_INPUT --> RS1
    RS1 --> RS1A
    RS2 --> RS_SCORE
    RS3 --> RS_SCORE
    
    PE_INPUT --> PS1
    PS1 --> PS1A
    PS2 --> PS_SCORE
    PS3 --> PS_SCORE
    
    DQS_SCORE --> FORMULA
    DHS_SCORE --> FORMULA
    USS_SCORE --> FORMULA
    RS_SCORE --> FORMULA
    PS_SCORE --> FORMULA
    FORMULA --> FINAL
    
    style ENGINE1 fill:#e8f5e9
    style ENGINE2 fill:#e8f5e9
    style ENGINE3 fill:#e8f5e9
    style ENGINE4 fill:#e8f5e9
    style ENGINE5 fill:#e8f5e9
    style COMBINE fill:#fff3e0
```

---

## 3. Confidence Assessment: Five Components

Detailed calculation of confidence in the trust score:

```mermaid
graph TB
    subgraph INPUT["📥 CONFIDENCE INPUTS"]
        DATA_COLL["Data available for<br/>assessment"]
        HISTORY["Historical<br/>record"]
        METRICS["Metric<br/>observations"]
    end
    
    subgraph COMP1["📊 DATA COVERAGE (30%)"]
        DC1["Count measurements<br/>available"]
        DC2["Expected: 16 metrics<br/>minimum"]
        DC3A["Coverage %<br/>= actual/expected"]
        DC3B["Score: Coverage % × 100"]
        DC_RESULT["Data Coverage<br/>(0-100)"]
    end
    
    subgraph COMP2["📅 HISTORICAL COVERAGE (25%)"]
        HC1["Time since first<br/>observation"]
        HC2A["Baseline: 90 days<br/>(production)"]
        HC2B["MVP: Any data ok"]
        HC3A["Decay function:<br/>min(days_observed/90, 1.0)"]
        HC3B["Score: decay × 100"]
        HC_RESULT["Historical Coverage<br/>(0-100)"]
    end
    
    subgraph COMP3["🎯 METRIC AVAILABILITY (20%)"]
        MA1["Count available<br/>metric categories"]
        MA2["Standard: 16 categories<br/>(accuracy, precision, recall,<br/>f1, loss, auc, etc.)"]
        MA3["Availability %<br/>= present/16"]
        MA4["Score: Availability % × 100"]
        MA_RESULT["Metric Availability<br/>(0-100)"]
    end
    
    subgraph COMP4["⏱️ EVIDENCE FRESHNESS (15%)"]
        EF1["Age of latest<br/>update"]
        EF2A["Fresh: 0-24h → 100%"]
        EF2B["Stale: 24-72h → 50%"]
        EF2C["Very stale: > 90d → 0%"]
        EF3["Score: decay_factor × 100"]
        EF_RESULT["Evidence Freshness<br/>(0-100)"]
    end
    
    subgraph COMP5["📉 STATISTICAL STABILITY (10%)"]
        SS1["Coefficient of Variation<br/>(CV) of observations"]
        SS2["CV = std_dev / mean"]
        SS3A["CV ≤ 0.30 → Stable → 100"]
        SS3B["0.30 < CV ≤ 1.0 → Moderate → 70"]
        SS3C["CV > 1.0 → Unstable → 30"]
        SS_RESULT["Statistical Stability<br/>(0-100)"]
    end
    
    subgraph COMBINE_CONF["🎲 CONFIDENCE FORMULA"]
        CONF_FORMULA["CONFIDENCE = <br/>0.30×DC + 0.25×HC<br/>+ 0.20×MA + 0.15×EF<br/>+ 0.10×SS"]
        CONF_SCORE["Confidence Score<br/>(0-100)"]
    end
    
    subgraph CLASSIFY["🏷️ CONFIDENCE CLASSIFICATION"]
        CONF_HIGH["≥ 90 → HIGH<br/>(Very confident)"]
        CONF_MED["70-89 → MEDIUM<br/>(Moderately confident)"]
        CONF_LOW["40-69 → LOW<br/>(Some doubt)"]
        CONF_INSUF["< 40 → INSUFFICIENT<br/>(Not enough data)"]
        FINAL_CLASS["Final Confidence<br/>Level"]
    end
    
    DATA_COLL --> DC1
    HISTORY --> HC1
    METRICS --> MA1
    
    DC1 --> DC2
    DC2 --> DC3A
    DC3A --> DC3B
    DC3B --> DC_RESULT
    
    HC1 --> HC2A
    HC2A --> HC3A
    HC3A --> HC3B
    HC3B --> HC_RESULT
    
    MA1 --> MA2
    MA2 --> MA3
    MA3 --> MA4
    MA4 --> MA_RESULT
    
    EF1 --> EF2A
    EF2A --> EF3
    EF3 --> EF_RESULT
    
    SS1 --> SS2
    SS2 --> SS3A
    SS3A --> SS_RESULT
    
    DC_RESULT --> CONF_FORMULA
    HC_RESULT --> CONF_FORMULA
    MA_RESULT --> CONF_FORMULA
    EF_RESULT --> CONF_FORMULA
    SS_RESULT --> CONF_FORMULA
    
    CONF_FORMULA --> CONF_SCORE
    CONF_SCORE --> CLASSIFY
    
    CLASSIFY --> CONF_HIGH
    CLASSIFY --> CONF_MED
    CLASSIFY --> CONF_LOW
    CLASSIFY --> CONF_INSUF
    
    CONF_HIGH --> FINAL_CLASS
    CONF_MED --> FINAL_CLASS
    CONF_LOW --> FINAL_CLASS
    CONF_INSUF --> FINAL_CLASS
    
    style COMP1 fill:#fff3e0
    style COMP2 fill:#fff3e0
    style COMP3 fill:#fff3e0
    style COMP4 fill:#fff3e0
    style COMP5 fill:#fff3e0
    style COMBINE_CONF fill:#f3e5f5
    style CLASSIFY fill:#f1f8e9
```

---

## 4. Decision Engine: Trust to Action

Maps trust score to decision with confidence guidance:

```mermaid
graph TD
    subgraph INPUT["📊 INPUTS"]
        TRUST["Trust Score<br/>(0-100)"]
        CONFIDENCE["Confidence Level<br/>(HIGH/MEDIUM/LOW/INSUF)"]
        ORG["Participant<br/>ID"]
    end
    
    subgraph TIER1["🟢 TIER 1: ALLOW (TRUST ≥ 75)"]
        T1_DESC["High trust in update"]
        T1_ACTIONS["✓ Include in aggregation<br/>✓ Use full weight<br/>✓ Log as approved<br/>✓ Monitor for patterns"]
    end
    
    subgraph TIER2["🟡 TIER 2: MONITOR (60 ≤ TRUST < 75)"]
        T2_DESC["Medium-high trust<br/>Needs monitoring"]
        T2A_HIGH["Confidence: HIGH"]
        T2A_ACTION["Include in aggregation<br/>(reduced weight tracking)"]
        T2B_MED["Confidence: MEDIUM"]
        T2B_ACTION["Include, flag for review"]
        T2C_LOW["Confidence: LOW"]
        T2C_ACTION["Include, escalate to manual"]
    end
    
    subgraph TIER3["🟠 TIER 3: REVIEW (40 ≤ TRUST < 60)"]
        T3_DESC["Borderline trust<br/>Manual review needed"]
        T3_ACTION["✓ Queue for manual review<br/>✓ Exclude from aggregation<br/>✓ Notify reviewer<br/>✓ Retry after decision"]
    end
    
    subgraph TIER4["🔴 TIER 4: BLOCK (TRUST < 40)"]
        T4_DESC["Very low trust<br/>Likely malicious"]
        T4_ACTIONS["✓ Reject update<br/>✓ Do NOT include<br/>✓ Isolate participant<br/>✓ Escalate to admin<br/>✓ Possible kick"]
    end
    
    subgraph SPECIAL["⚠️ SPECIAL CASES"]
        GATE_FAIL["Hard Gate Fail"]
        GATE_FAIL_ACTION["→ Reject immediately<br/>(TIER 4)"]
        
        NO_CONFIDENCE["No Confidence Data"]
        NO_CONFIDENCE_ACTION["→ MONITOR tier<br/>(assume medium)"]
    end
    
    subgraph OUTPUT["📤 DECISION OUTPUT"]
        DECISION_STATE["Decision Record:<br/>- Org ID<br/>- Trust Score<br/>- Confidence<br/>- Action<br/>- Timestamp<br/>- Reason"]
    end
    
    INPUT --> TRUST
    INPUT --> CONFIDENCE
    INPUT --> ORG
    
    TRUST --> TIER1
    TRUST --> TIER2
    TRUST --> TIER3
    TRUST --> TIER4
    
    CONFIDENCE --> TIER2
    CONFIDENCE --> TIER3
    
    GATE_FAIL --> GATE_FAIL_ACTION
    GATE_FAIL_ACTION --> TIER4
    
    NO_CONFIDENCE --> NO_CONFIDENCE_ACTION
    NO_CONFIDENCE_ACTION --> TIER2
    
    T1_DESC --> T1_ACTIONS
    T2_DESC --> T2A_HIGH
    T2A_HIGH --> T2A_ACTION
    T2_DESC --> T2B_MED
    T2B_MED --> T2B_ACTION
    T2_DESC --> T2C_LOW
    T2C_LOW --> T2C_ACTION
    
    T1_ACTIONS --> OUTPUT
    T2A_ACTION --> OUTPUT
    T2B_ACTION --> OUTPUT
    T2C_ACTION --> OUTPUT
    T3_ACTION --> OUTPUT
    T4_ACTIONS --> OUTPUT
    
    style TIER1 fill:#c8e6c9
    style TIER2 fill:#fff9c4
    style TIER3 fill:#ffe0b2
    style TIER4 fill:#ffcdd2
    style SPECIAL fill:#f3e5f5
```

---

## 5. Fallback Mechanisms

Recovery paths when updates don't meet safety criteria:

```mermaid
graph TD
    subgraph PRIMARY["🟢 PRIMARY PATHS"]
        ALLOW["ALLOW Decision"]
        MONITOR["MONITOR Decision"]
    end
    
    subgraph ESCALATION["🟡 ESCALATION PATHS"]
        REVIEW["REVIEW Decision"]
        BLOCK["BLOCK Decision"]
    end
    
    subgraph FALLBACK1["🚫 Fallback 1: Hard Gate Failure"]
        FB1_TRIGGER["Trigger: Structural<br/>validation fails"]
        FB1_ACTIONS["1. Log failure<br/>2. Mark participant<br/>3. Skip update<br/>4. Track failures"]
        FB1_RESULT["Result: Update rejected<br/>Participant marked<br/>suspicious"]
    end
    
    subgraph FALLBACK2["🚫 Fallback 2: Anomalous Trust"]
        FB2_TRIGGER["Trigger: Trust score<br/>sudden change"]
        FB2_CHECK["Check if:<br/>- Anomaly expected<br/>- Data quality issue<br/>- Drift detected"]
        FB2_ACTIONS["1. Flag update<br/>2. Trigger manual review<br/>3. Hold aggregation<br/>4. Investigate"]
        FB2_RESULT["Result: Manual review<br/>queue grows"]
    end
    
    subgraph FALLBACK3["⚠️ Fallback 3: Scorer Failure"]
        FB3_TRIGGER["Trigger: Confidence<br/>score unavailable"]
        FB3_DEFAULT["Fallback to<br/>medium confidence"]
        FB3_ACTIONS["1. Use conservative<br/>   estimate<br/>2. Log issue<br/>3. Lower TRUST by 10%"]
        FB3_RESULT["Result: Update scored<br/>conservatively"]
    end
    
    subgraph FALLBACK4["🔄 Fallback 4: Review Backlog"]
        FB4_TRIGGER["Trigger: Manual review<br/>queue overflows"]
        FB4_BATCH["Batch reviews:<br/>Process in rounds"]
        FB4_ACTIONS["1. Group by<br/>   participant<br/>2. Prioritize<br/>3. Review with<br/>   confidence band"]
        FB4_RESULT["Result: Cleared backlog<br/>via batch processing"]
    end
    
    subgraph FALLBACK5["🔙 Fallback 5: Partial Aggregation"]
        FB5_TRIGGER["Trigger: Many BLOCKs<br/>or REVIEWs"]
        FB5_CHECK["Check if:<br/>- Normal round<br/>- System issue<br/>- Attack scenario"]
        FB5_POLICY["Policy options:<br/>1. Use ALLOW only<br/>2. Add MONITOR<br/>3. Manual vote"]
        FB5_RESULT["Result: Use subset<br/>of updates"]
    end
    
    subgraph FALLBACK6["⏮️ Fallback 6: Model Rollback"]
        FB6_TRIGGER["Trigger: Global model<br/>validation fails"]
        FB6_ACTIONS["1. Revert to<br/>   prior model<br/>2. Skip aggregation<br/>3. Alert admin<br/>4. Log incident"]
        FB6_RESULT["Result: Safety<br/>maintained, retry<br/>next round"]
    end
    
    PRIMARY -.-> FALLBACK1
    ESCALATION -.-> FALLBACK2
    ESCALATION -.-> FALLBACK3
    FALLBACK1 --> FALLBACK4
    FALLBACK2 --> FALLBACK4
    FALLBACK3 --> FALLBACK5
    FALLBACK4 --> FALLBACK5
    FALLBACK5 --> FALLBACK6
    
    style PRIMARY fill:#c8e6c9
    style ESCALATION fill:#ffe0b2
    style FALLBACK1 fill:#ffcdd2
    style FALLBACK2 fill:#ffcdd2
    style FALLBACK3 fill:#ffcdd2
    style FALLBACK4 fill:#fff9c4
    style FALLBACK5 fill:#ffe0b2
    style FALLBACK6 fill:#f3e5f5
```

---

## 6. Recovery Mechanisms

System recovery from failures:

```mermaid
graph TD
    subgraph DETECTION["🔍 FAILURE DETECTION"]
        DETECT1["Hard Gate Failure"]
        DETECT2["Score Anomaly"]
        DETECT3["Model Degradation"]
        DETECT4["Participant Silent"]
    end
    
    subgraph IMPACT["⚠️ IMPACT ASSESSMENT"]
        IMPACT1["Single participant"]
        IMPACT2["Multiple participants"]
        IMPACT3["System level"]
    end
    
    subgraph RECOVERY["🔧 RECOVERY STRATEGY"]
        REC1["Strategy 1:<br/>Isolate Participant"]
        REC1_STEPS["1. Mark as suspicious<br/>2. Exclude from round<br/>3. Retry next round<br/>4. Monitor recovery"]
        
        REC2["Strategy 2:<br/>Manual Review"]
        REC2_STEPS["1. Queue for human<br/>2. Admin decision<br/>3. Whitelist/Blacklist<br/>4. Proceed"]
        
        REC3["Strategy 3:<br/>Rollback Round"]
        REC3_STEPS["1. Undo aggregation<br/>2. Restore prior model<br/>3. Log incident<br/>4. Retry"]
        
        REC4["Strategy 4:<br/>Reduced Aggregation"]
        REC4_STEPS["1. Use ALLOW-only<br/>2. Exclude MONITOR/REVIEW<br/>3. Aggregate safely<br/>4. Monitor outcome"]
    end
    
    subgraph VALIDATION["✅ VALIDATION"]
        VAL1["Check restored state"]
        VAL2["Verify model weights"]
        VAL3["Validate accuracy"]
        VAL4["Audit log entries"]
    end
    
    subgraph RESUME["▶️ RESUME OPERATION"]
        RESUME_STATE["Resume from<br/>Validated State"]
        CONTINUE["Continue to<br/>Next Round"]
    end
    
    DETECT1 --> IMPACT1
    DETECT2 --> IMPACT2
    DETECT3 --> IMPACT3
    DETECT4 --> IMPACT1
    
    IMPACT1 --> REC1
    IMPACT2 --> REC2
    IMPACT3 --> REC3
    
    IMPACT1 --> REC4
    IMPACT2 --> REC4
    
    REC1 --> REC1_STEPS
    REC2 --> REC2_STEPS
    REC3 --> REC3_STEPS
    REC4 --> REC4_STEPS
    
    REC1_STEPS --> VALIDATION
    REC2_STEPS --> VALIDATION
    REC3_STEPS --> VALIDATION
    REC4_STEPS --> VALIDATION
    
    VALIDATION --> VAL1
    VALIDATION --> VAL2
    VALIDATION --> VAL3
    VALIDATION --> VAL4
    
    VAL1 --> RESUME_STATE
    VAL2 --> RESUME_STATE
    VAL3 --> RESUME_STATE
    VAL4 --> RESUME_STATE
    
    RESUME_STATE --> CONTINUE
    CONTINUE -.->|Next Round| DETECT1
    
    style DETECTION fill:#ffebee
    style IMPACT fill:#fff3e0
    style RECOVERY fill:#ffe0b2
    style VALIDATION fill:#e8f5e9
    style RESUME fill:#c8e6c9
```

---

## 7. Complete Decision Flow: Update to Action

End-to-end decision flow showing all states and transitions:

```mermaid
graph LR
    START["Start:<br/>Update Received"] --> GATE["Hard<br/>Safety Gate"]
    
    GATE -->|FAIL| REJECT["❌ REJECT<br/>Update"]
    GATE -->|PASS| DQS_ENG["DQS<br/>Engine"]
    
    DQS_ENG --> DHS_ENG["DHS<br/>Engine"]
    DHS_ENG --> USS_ENG["USS<br/>Engine"]
    USS_ENG --> RS_ENG["RS<br/>Engine"]
    RS_ENG --> PS_ENG["PS<br/>Engine"]
    
    PS_ENG --> TRUST_CALC["Trust<br/>Calculation"]
    TRUST_CALC --> CONF_CALC["Confidence<br/>Calculation"]
    
    CONF_CALC --> DECISION["Decision<br/>Engine"]
    
    DECISION -->|TRUST ≥ 75| ALLOW["🟢 ALLOW<br/>(Include)"]
    DECISION -->|60 ≤ TRUST < 75| MONITOR["🟡 MONITOR<br/>(Track)"]
    DECISION -->|40 ≤ TRUST < 60| REVIEW["🟠 REVIEW<br/>(Manual)"]
    DECISION -->|TRUST < 40| BLOCK["🔴 BLOCK<br/>(Reject)"]
    
    ALLOW --> AGGREGATE["Aggregation"]
    MONITOR --> CHECK_CONF{"Confidence<br/>High?"}
    CHECK_CONF -->|Yes| AGGREGATE
    CHECK_CONF -->|No| MANUAL["Manual<br/>Review"]
    
    REVIEW --> MANUAL
    MANUAL --> ADMIN_DECISION{"Approved?"}
    ADMIN_DECISION -->|Yes| AGGREGATE
    ADMIN_DECISION -->|No| REJECT
    
    BLOCK --> ISOLATE["Isolate<br/>Participant"]
    ISOLATE --> REJECT
    
    AGGREGATE --> UPDATE["Update<br/>Global Model"]
    REJECT --> SKIP["Skip to<br/>Next Round"]
    
    UPDATE --> NEXT["Ready for<br/>Next Round"]
    SKIP --> NEXT
    
    style START fill:#e3f2fd
    style GATE fill:#ffebee
    style ALLOW fill:#c8e6c9
    style MONITOR fill:#fff9c4
    style REVIEW fill:#ffe0b2
    style BLOCK fill:#ffcdd2
    style AGGREGATE fill:#e0f2f1
    style UPDATE fill:#e8f5e9
    style NEXT fill:#c8e6c9
    style REJECT fill:#ff6b6b
```

---

## Trust Score Reference Table

Quick reference for decision boundaries:

```
┌──────────────────┬────────────────┬───────────────────────────┐
│ Trust Score      │ Decision       │ Typical Action            │
├──────────────────┼────────────────┼───────────────────────────┤
│ 90-100           │ ALLOW          │ Include, high priority    │
│ 75-89            │ ALLOW          │ Include normally          │
│ 75               │ ALLOW/MONITOR  │ Borderline (HIGH conf OK) │
│ 60-74            │ MONITOR        │ Include with tracking     │
│ 40-59            │ REVIEW         │ Queue for manual review   │
│ 30-39            │ BLOCK (likely) │ Likely malicious          │
│ <30              │ BLOCK          │ Definitely malicious      │
│ <0 or >100       │ ERROR          │ Scoring failure, reject   │
└──────────────────┴────────────────┴───────────────────────────┘
```

---

## Confidence Level Interpretation

```
┌────────────────────┬──────────────┬────────────────────────────┐
│ Confidence Score   │ Level        │ Meaning                    │
├────────────────────┼──────────────┼────────────────────────────┤
│ 90-100             │ HIGH         │ Very certain in trust score│
│ 70-89              │ MEDIUM       │ Moderately certain         │
│ 40-69              │ LOW          │ Some uncertainty           │
│ 0-39               │ INSUFFICIENT │ Not enough evidence        │
└────────────────────┴──────────────┴────────────────────────────┘
```

---

## Document History

| Version | Date | Author | Notes |
|---------|------|--------|-------|
| 1.0 | 2024 | Team | Initial decision flow architecture |

**End of Decision Flow**
