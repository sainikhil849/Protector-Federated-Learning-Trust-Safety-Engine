# Formulas: Mathematical Reference for All Scores

This is the canonical mathematical reference for all scoring calculations in Protector Uttam. Use this for implementation, validation, and documentation.

---

## 1. Data Quality Score (DQS)

### 1.1 Schema Score (SS)

$$SS = \frac{\text{valid\_required\_checks}}{\text{total\_required\_checks}} \times 100$$

**Valid Required Checks:**
$$\text{valid\_required\_checks} = \sum_{i=1}^{n} \mathbb{1}[\text{field}_i \text{ present} \land \text{type\_matches} \land \text{constraints\_satisfied}]$$

**Output Range:** $[0, 100]$

---

### 1.2 Completeness Score (CS)

**Simple:**
$$\text{missing\_ratio} = \frac{\text{missing\_values}}{\text{total\_expected\_values}}$$

$$CS = 100 \times \max(0, 1 - \text{missing\_ratio})$$

**With Field Weights:**
$$\text{weighted\_missing} = \sum_{j=1}^{m} w_j \times \frac{\text{missing}_j}{\text{total\_records}}$$

$$CS = 100 \times (1 - \text{weighted\_missing})$$

where $w_j$ = weight for field $j$, $\sum w_j = 1$

**Output Range:** $[0, 100]$

---

### 1.3 Validity Score (VS)

$$\text{valid\_values} = \sum_{i=1}^{n} \mathbb{1}[\text{type\_validator}(v_i) \land \text{domain\_validator}(v_i)]$$

$$VS = \frac{\text{valid\_values}}{\text{total\_non\_null\_values}} \times 100$$

**Output Range:** $[0, 100]$

---

### 1.4 Outlier Health Score (OHS)

#### Method 1: Interquartile Range (IQR)

$$IQR = Q_3 - Q_1$$

$$\text{lower\_fence} = Q_1 - \tau \times IQR$$

$$\text{upper\_fence} = Q_3 + \tau \times IQR$$

$$\text{is\_outlier}(x) = \mathbb{1}[x < \text{lower\_fence} \lor x > \text{upper\_fence}]$$

$$OHS = \left(1 - \frac{\sum_{i=1}^{n} \text{is\_outlier}(x_i)}{n}\right) \times 100$$

where $\tau = 1.5$ (Tukey's standard)

#### Method 2: Median Absolute Deviation (MAD)

$$MAD = \text{median}(|x_i - \text{median}(x)|)$$

$$\text{robust\_z}_i = \frac{0.6745 \times (x_i - \text{median}(x))}{MAD + \epsilon}$$

$$\text{is\_outlier}(x_i) = \mathbb{1}[|\text{robust\_z}_i| > \tau]$$

$$OHS = \left(1 - \frac{\sum_{i=1}^{n} \text{is\_outlier}(x_i)}{n}\right) \times 100$$

where $\tau = 3.0$, $\epsilon = 10^{-10}$

#### Method 3: Z-Score

$$z_i = \frac{x_i - \mu}{\sigma + \epsilon}$$

$$\text{is\_outlier}(x_i) = \mathbb{1}[|z_i| > \tau]$$

$$OHS = \left(1 - \frac{\sum_{i=1}^{n} \text{is\_outlier}(x_i)}{n}\right) \times 100$$

where $\tau = 3.0$, $\epsilon = 10^{-10}$

**Output Range:** $[0, 100]$

---

### 1.5 Sample Sufficiency Score (SuS)

**Simple Formula:**
$$\text{SuS} = \min\left(100, \frac{\text{current\_samples}}{\text{minimum\_required\_samples}} \times 100\right)$$

**With Recommended Threshold:**

$$\text{SuS} = \begin{cases}
\frac{\text{current}}{\text{minimum}} \times 50 & \text{if current} < \text{minimum} \\
50 + 50 \times \frac{\text{current} - \text{minimum}}{\text{recommended} - \text{minimum}} & \text{if minimum} \leq \text{current} < \text{recommended} \\
100 & \text{if current} \geq \text{recommended}
\end{cases}$$

**Output Range:** $[0, 100]$

---

### 1.6 Final Data Quality Score

$$\boxed{DQS = 0.25 \times SS + 0.25 \times CS + 0.15 \times VS + 0.20 \times OHS + 0.15 \times \text{SuS}}$$

**Weights (INITIAL PROTOTYPE - CONFIGURABLE):**
- Schema: 0.25
- Completeness: 0.25
- Validity: 0.15
- Outlier Health: 0.20
- Sample Sufficiency: 0.15

**Normalization:** $DQS \in [0, 100]$

---

## 2. Drift Health Score (DHS)

### 2.1 Population Stability Index (PSI)

$$PSI = \sum_{i=1}^{k} (p^{\text{actual}}_i - p^{\text{expected}}_i) \times \ln\left(\frac{p^{\text{actual}}_i}{p^{\text{expected}}_i}\right)$$

where:
- $k$ = number of bins
- $p^{\text{actual}}_i$ = fraction of current data in bin $i$
- $p^{\text{expected}}_i$ = fraction of historical data in bin $i$
- $\ln$ = natural logarithm

**With Laplace Smoothing:**
$$p^{\text{smoothed}}_i = \frac{c_i + \alpha}{N + k \times \alpha}$$

where:
- $c_i$ = count of samples in bin $i$
- $N$ = total samples
- $\alpha$ = smoothing factor (default: 0.5)
- $k$ = number of bins

$$PSI_{\text{smoothed}} = \sum_{i=1}^{k} (p^{\text{actual,smooth}}_i - p^{\text{expected,smooth}}_i) \times \ln\left(\frac{p^{\text{actual,smooth}}_i}{p^{\text{expected,smooth}}_i}\right)$$

**Interpretation:**
- $PSI < 0.1$: negligible drift
- $0.1 \leq PSI < 0.25$: small drift
- $0.25 \leq PSI < 0.50$: medium drift
- $PSI \geq 0.50$: large drift

---

### 2.2 PSI-to-Health Score Conversion (Linear)

$$DHS = \begin{cases}
100 & \text{if } PSI \leq \tau_{\text{negligible}} \\
90 + 10 \times \frac{\tau_{\text{small}} - PSI}{\tau_{\text{small}} - \tau_{\text{negligible}}} & \text{if } \tau_{\text{negligible}} < PSI \leq \tau_{\text{small}} \\
70 + 20 \times \frac{\tau_{\text{medium}} - PSI}{\tau_{\text{medium}} - \tau_{\text{small}}} & \text{if } \tau_{\text{small}} < PSI \leq \tau_{\text{medium}} \\
\max(0, 70 - 70 \times \frac{PSI - \tau_{\text{medium}}}{\tau_{\text{medium}}}) & \text{if } PSI > \tau_{\text{medium}}
\end{cases}$$

**Default Thresholds:**
- $\tau_{\text{negligible}} = 0.1$
- $\tau_{\text{small}} = 0.25$
- $\tau_{\text{medium}} = 0.50$

**Alternative (Sigmoid Conversion):**
$$DHS = \frac{100}{1 + \exp(k \times (PSI - PSI_{\text{inflection}}))}$$

where $k = 10$ (steepness), $PSI_{\text{inflection}} = 0.25$ (transition point)

**Output Range:** $[0, 100]$

---

### 2.3 Multi-Feature Drift Aggregation

**Average:**
$$DHS_{\text{final}} = \frac{1}{m} \sum_{j=1}^{m} DHS_j$$

**Weighted Average:**
$$DHS_{\text{final}} = \sum_{j=1}^{m} w_j \times DHS_j \quad (\sum w_j = 1)$$

**Minimum (Conservative):**
$$DHS_{\text{final}} = \min_j(DHS_j)$$

**Maximum Drift:**
$$DHS_{\text{final}} = DHS_{\arg\max_j(PSI_j)}$$

---

## 3. Update Safety Score (USS)

### 3.1 Structural Validity Score (SVS)

$$\text{invalid\_ratio} = \frac{n_{\text{NaN}} + n_{\text{Inf}} + n_{\text{complex}}}{\text{total\_parameters}}$$

$$SVS = \begin{cases}
1.0 & \text{if invalid\_ratio} = 0 \\
0.8 & \text{if } 0 < \text{invalid\_ratio} < 0.001 \\
0.5 & \text{if } 0.001 \leq \text{invalid\_ratio} < 0.01 \\
0.2 & \text{if } 0.01 \leq \text{invalid\_ratio} < 0.1 \\
0.0 & \text{if } \text{invalid\_ratio} \geq 0.1
\end{cases}$$

**Output Range:** $[0, 1]$

---

### 3.2 Magnitude Score (MS)

**Step 1: Robust Statistics**
$$\text{median}_{\Delta W} = \text{median}(||\Delta W_i||)$$

$$MAD = \text{median}(|||\Delta W_i|| - \text{median}_{\Delta W}||)$$

**Step 2: Robust Z-Score**
$$z_{\text{robust}} = \frac{||\Delta W_{\text{current}}|| - \text{median}_{\Delta W}}{0.6745 \times (MAD + \epsilon)}$$

**Step 3: Layer-Wise Score**
$$MS_{\text{layer}} = \begin{cases}
1.0 & \text{if } |z_{\text{robust}}| \leq \tau \\
0.5 + 0.5 \times \left(1 - \frac{|z_{\text{robust}}|}{2\tau}\right) & \text{if } \tau < |z_{\text{robust}}| \leq 2\tau \\
0.0 & \text{if } |z_{\text{robust}}| > 2\tau
\end{cases}$$

where $\tau = 3.0$ (outlier threshold)

**Step 4: Aggregate**
$$MS = \frac{1}{L} \sum_{l=1}^{L} MS_{\text{layer}_l}$$

where $L$ = number of layers

**Output Range:** $[0, 1]$

---

### 3.3 Freshness Score (FS)

$$\text{age\_hours} = \frac{(\text{timestamp\_now} - \text{timestamp\_created})}{3600}$$

$$FS = \begin{cases}
1.0 & \text{if age\_hours} \leq 1 \\
0.99 & \text{if } 1 < \text{age\_hours} \leq 24 \\
0.95 - 0.05 \times \frac{\text{age\_hours} - 24}{48} & \text{if } 24 < \text{age\_hours} \leq 72 \\
0.8 - 0.5 \times \frac{\text{age\_hours} - 72}{T_{\text{max}} - 72} & \text{if } 72 < \text{age\_hours} \leq T_{\text{max}} \\
\max(0.1, 0.3 - 0.2 \times \frac{\text{age\_hours} - T_{\text{max}}}{T_{\text{max}}}) & \text{if } \text{age\_hours} > T_{\text{max}}
\end{cases}$$

where $T_{\text{max}} = 168$ hours (7 days, configurable)

**Output Range:** $[0.1, 1.0]$

---

### 3.4 Consistency Score (CS)

**Step 1: Direction Similarity**
$$\text{direction\_sim} = \frac{\Delta W_{\text{current}} \cdot \text{mean}(\Delta W_{\text{historical}})}{||\Delta W_{\text{current}}|| \times ||\text{mean}(\Delta W_{\text{historical}})||}$$

**Step 2: Magnitude Consistency**
$$\text{mag\_ratio} = \frac{||\Delta W_{\text{current}}||}{\text{median}(||\Delta W_{\text{historical}}||) + \epsilon}$$

$$CS_{\text{mag}} = \begin{cases}
1.0 & \text{if } 0.5 < \text{mag\_ratio} < 2.0 \\
0.8 & \text{if } (0.25 < \text{mag\_ratio} \leq 0.5) \lor (2.0 < \text{mag\_ratio} \leq 4.0) \\
0.5 & \text{if } (0.1 < \text{mag\_ratio} \leq 0.25) \lor (4.0 < \text{mag\_ratio} \leq 10.0) \\
0.2 & \text{if } (\text{mag\_ratio} \leq 0.1) \lor (\text{mag\_ratio} > 10.0)
\end{cases}$$

**Step 3: Combine**
$$CS = \max(0, \min(1, 0.7 \times \text{direction\_sim} + 0.3 \times CS_{\text{mag}}))$$

**Output Range:** $[0, 1]$

---

### 3.5 Final Update Safety Score

$$\boxed{USS = 0.35 \times SVS + 0.30 \times MS + 0.20 \times FS + 0.15 \times CS}$$

**Scaling to [0, 100]:**
$$USS_{\text{final}} = USS \times 100$$

**Output Range:** $[0, 100]$

**Weights (INITIAL PROTOTYPE - CONFIGURABLE):**
- Structural Validity: 0.35
- Magnitude: 0.30
- Freshness: 0.20
- Consistency: 0.15

---

## 4. Reliability Score (RS)

### 4.1 Availability Score (AS)

$$AS = \frac{\text{successful\_submits}}{\text{total\_rounds}} \times 100$$

**Output Range:** $[0, 100]$

---

### 4.2 Heartbeat Health Score (HS)

$$\text{intervals} = \{\text{timestamp}_{i+1} - \text{timestamp}_{i} : i = 0..n-1\}$$

$$\text{median\_interval} = \text{median}(\text{intervals})$$

$$\text{median\_deviation} = \text{median}(|\text{interval}_i - \text{median\_interval}|)$$

$$\text{consistency\_ratio} = \frac{\text{median\_interval}}{\text{median\_deviation} + \epsilon}$$

$$HS = \begin{cases}
100 & \text{if consistency\_ratio} > 5 \\
90 & \text{if } 3 \leq \text{consistency\_ratio} \leq 5 \\
70 & \text{if } 2 \leq \text{consistency\_ratio} < 3 \\
50 & \text{if } 1 \leq \text{consistency\_ratio} < 2 \\
30 & \text{if consistency\_ratio} < 1
\end{cases}$$

**Output Range:** $[0, 100]$

---

### 4.3 Success Rate Score (SRS)

$$SRS = \frac{\text{accepted}}{\text{total\_updates}} \times 100$$

**Output Range:** $[0, 100]$

---

### 4.4 Latency Health Score (LHS)

$$\text{fraction\_on\_time} = \frac{\sum_{i=1}^{n} \mathbb{1}[\text{latency}_i \leq T_{\text{threshold}}]}{n}$$

$$LHS = \begin{cases}
100 & \text{if fraction\_on\_time} \geq 0.95 \\
80 + 20 \times \frac{\text{fraction\_on\_time} - 0.80}{0.15} & \text{if } 0.80 \leq \text{fraction\_on\_time} < 0.95 \\
50 + 30 \times \frac{\text{fraction\_on\_time} - 0.60}{0.20} & \text{if } 0.60 \leq \text{fraction\_on\_time} < 0.80 \\
\max(10, 50 \times \text{fraction\_on\_time}) & \text{if fraction\_on\_time} < 0.60
\end{cases}$$

**Output Range:** $[0, 100]$

---

### 4.5 Consecutive Failure Penalty

$$\text{consecutive\_failures} = \text{count of recent blocked updates before first success}$$

$$\text{penalty} = \begin{cases}
0 & \text{if consecutive\_failures} = 0 \\
-10 & \text{if consecutive\_failures} = 1 \\
-25 & \text{if consecutive\_failures} = 2 \\
-50 & \text{if consecutive\_failures} \geq 3
\end{cases}$$

**Output Range:** $[-50, 0]$

---

### 4.6 Final Reliability Score

$$RS_{\text{raw}} = 0.35 \times AS + 0.25 \times HS + 0.20 \times SRS + 0.20 \times LHS$$

$$\boxed{RS = \max(0, \min(100, RS_{\text{raw}} + \text{penalty}))}$$

**Weights (INITIAL PROTOTYPE - CONFIGURABLE):**
- Availability: 0.35
- Heartbeat Health: 0.25
- Success Rate: 0.20
- Latency Health: 0.20

**Output Range:** $[0, 100]$

---

## 5. Performance Score (PS)

### 5.1 Metric Computation

**Classification (F1 Score):**
$$F1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}$$

**Regression (Mean Absolute Error):**
$$MAE = \frac{1}{n} \sum_{i=1}^{n} |y_{\text{true},i} - y_{\text{pred},i}|$$

**Ranking (NDCG@k):**
$$NDCG@k = \frac{DCG@k}{IDCG@k}$$

$$DCG@k = \sum_{i=1}^{k} \frac{2^{\text{rel}_i} - 1}{\log_2(i + 1)}$$

---

### 5.2 Performance Health Calculation

**For Higher-is-Better Metrics** (F1, NDCG, AUC):
$$\Delta = \frac{\text{current\_metric} - \text{baseline\_metric}}{\text{baseline\_metric} + \epsilon}$$

$$PS = \min(100, 100 \times (1 + \Delta))$$

**For Lower-is-Better Metrics** (MAE, MSE, loss):
$$\Delta = \frac{\text{baseline\_metric} - \text{current\_metric}}{\text{baseline\_metric} + \epsilon}$$

$$PS = \min(100, 100 \times (1 + \Delta))$$

**Output Range:** $[0, 100]$

---

### 5.3 Fairness Penalty

$$\text{slice\_deltas} = \{\Delta_j : j = \text{all slices}\}$$

$$\text{fairness\_variance} = \max(\text{slice\_deltas}) - \min(\text{slice\_deltas})$$

$$\text{penalty} = \begin{cases}
0 & \text{if fairness\_variance} < 0.02 \\
-5 & \text{if } 0.02 \leq \text{fairness\_variance} < 0.05 \\
-15 & \text{if } 0.05 \leq \text{fairness\_variance} < 0.10 \\
-30 & \text{if fairness\_variance} \geq 0.10
\end{cases}$$

**Output Range:** $[-30, 0]$

---

### 5.4 Final Performance Score

$$\boxed{PS = \max(0, \min(100, PS_{\text{base}} + \text{fairness\_penalty}))}$$

**Output Range:** $[0, 100]$

---

## 6. Composite Trust Score

### 6.1 Aggregate Trust Calculation

$$\boxed{\text{TRUST} = 0.25 \times DQS + 0.25 \times DHS + 0.20 \times USS + 0.20 \times RS + 0.10 \times PS}$$

**Weights (INITIAL PROTOTYPE - CONFIGURABLE):**
- Data Quality Score: 0.25
- Drift Health Score: 0.25
- Update Safety Score: 0.20
- Reliability Score: 0.20
- Performance Score: 0.10

**Output Range:** $[0, 100]$

---

### 6.2 Confidence Interval

For each dimension $i$, compute standard error $\sigma_i$.

$$\sigma_{\text{total}} = \sqrt{\sum_{i=1}^{5} (w_i \times \sigma_i)^2}$$

**Final Result:**
$$\text{TRUST} = \text{TRUST\_mean} \pm \sigma_{\text{total}} \quad \text{(95\% confidence)}$$

---

### 6.3 Decision Thresholds

$$\text{Decision} = \begin{cases}
\text{ALLOW} & \text{if } \text{TRUST} \geq 0.75 \\
\text{MONITOR} & \text{if } 0.60 \leq \text{TRUST} < 0.75 \\
\text{REVIEW} & \text{if } 0.40 \leq \text{TRUST} < 0.60 \\
\text{BLOCK} & \text{if } \text{TRUST} < 0.40
\end{cases}$$

(Thresholds configurable per domain)

---

## 7. Implementation Checklist

- [ ] All constants ($\tau$, smoothing factors, thresholds) are named and configurable
- [ ] All division operations include $\epsilon$ safeguard against division by zero
- [ ] All output ranges are clamped explicitly
- [ ] NaN and Inf values handled gracefully throughout
- [ ] Intermediate calculations logged for auditability
- [ ] Edge cases documented in code comments
- [ ] Unit tests written for each formula
- [ ] Test coverage >90%

---

**Document Status:** Complete reference for implementation.

**Last Updated:** [Date prototype specifications completed]
