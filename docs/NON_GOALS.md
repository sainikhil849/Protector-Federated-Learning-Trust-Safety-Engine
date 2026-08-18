# Non-Goals: What Protector Uttam Does NOT Do

## Critical Distinctions

The following capabilities are **explicitly out of scope** for Protector Uttam. Understanding what we don't do is as important as understanding what we do.

---

## ❌ We Do NOT Prove Trustworthiness

### What We Don't Claim

- "This participant is definitely trustworthy"
- "This participant's data quality is certified"
- "This participant is following best practices"
- "This participant is honest"
- "We guarantee this update is safe"

### Why This Matters

Federated learning's fundamental constraint is that the central aggregator cannot inspect raw training data. Therefore:

1. **No cryptographic proof of data quality exists** — You can't mathematically prove someone's training data was collected correctly
2. **No behavioral guarantee is possible** — A participant can behave well for years then send a poisoned update
3. **Confidence ≠ Certainty** — We can observe operational signals; we cannot prove ground truth

### What We Actually Do

- "Based on observed evidence, this update appears operationally safe with 87% confidence (±12%)"
- "This update is statistically anomalous; recommend human review"
- "This participant's track record shows X pattern; the current update deviates by Y"

---

## ❌ We Do NOT Replace Regulatory Compliance

### What We Don't Do

- Certify that data handling complies with GDPR, HIPAA, etc.
- Audit participant data governance practices
- Verify contractual compliance between consortium members
- Replace compliance officers or legal review
- Provide legal advice or liability guarantees

### Why This Matters

Federated learning operates within a legal and regulatory framework. Protector Uttam is a technical control, not a legal one.

### What We Actually Do

- Provide complete, auditable decision trails for regulators to review
- Enable transparent governance that satisfies audit requirements
- Document that trust decisions were made systematically (not arbitrarily)
- Support compliance through traceability, not guarantee it

---

## ❌ We Do NOT Optimize Model Performance

### What We Don't Do

- Improve the global model's accuracy directly
- Select "best" updates for aggregation
- Replace federated learning algorithms (e.g., FedAvg, FedProx)
- Tune hyperparameters or training procedures
- Perform model selection or ensemble learning

### Why This Matters

Protector Uttam sits *before* aggregation. Its job is safety gating, not optimization.

**Protector Uttam:** "Is this update safe to aggregate?"

**Federated Learning Algorithm:** "How should we combine accepted updates?"

These are orthogonal concerns.

### What We Actually Do

- **Enable** model performance improvement by making aggregation safer
- Flag updates that would cause performance degradation
- Allow more aggressive aggregation policies (because safety is gated)
- Provide metadata for downstream optimization algorithms

---

## ❌ We Do NOT Enforce Policies

### What We Don't Do

- Make final accept/reject decisions (system or human does)
- Prevent bad updates from being used elsewhere
- Punish or isolate bad participants
- Revoke participant access
- Modify model parameters

### Why This Matters

Protector Uttam is a **recommendation and monitoring engine**, not a **policy enforcement mechanism**. The decision to act on our recommendations belongs to humans or organizational policy.

### What We Actually Do

- Recommend ALLOW, MONITOR, BLOCK, or REVIEW
- Provide decision trails so humans can override if needed
- Enable policy engines to make informed decisions
- Flag issues for human review without unilateral action

---

## ❌ We Do NOT Work With Raw Data

### What We Don't Do

- Access participant training datasets
- Inspect raw features or labels
- Perform data quality checks on raw data
- Identify data leakage or privacy violations
- Certify data governance practices

### Why This Matters

Federated learning's privacy property depends on raw data staying local. Protector Uttam respects this boundary.

### What We Actually Do

- Work exclusively with model updates (gradients, weights, metadata)
- Infer data quality signals from model behavior
- Make safety decisions without data access
- Maintain privacy-by-architecture compatibility

---

## ❌ We Do NOT Detect All Poisoning Attacks

### What We Don't Claim

- "All poisoned updates will be detected"
- "We prevent all adversarial attacks"
- "Your system is immune to model poisoning"
- "We catch sophisticated, distributed attacks"

### Why This Matters

An adversary with full knowledge of our detection mechanisms can craft updates designed to evade them. This is fundamental to adversarial ML.

### What We Actually Do

- Detect common, naive poisoning patterns (>90% detection rate on typical attacks)
- Flag suspicious updates even when we're not certain they're poisoned
- Provide monitoring that makes repeated poisoning attempts visible
- Support human experts in investigating subtle anomalies

### What We Explicitly Cannot Detect

- **Subtle data quality drift** that doesn't cause statistical anomalies (only shows up as slow accuracy decline)
- **Sophisticated, adaptive attacks** designed to evade our specific detection methods
- **Coordinated poisoning** across multiple participants (distributed Byzantine resilience requires different mechanisms)
- **Intentional data labeling errors** that look statistically valid (can't inspect ground truth labels)
- **Training procedure bugs** that aren't reflected in model parameters (must assume model parameters reflect actual training)

---

## ❌ We Do NOT Provide Cryptographic Guarantees

### What We Don't Claim

- "We prove with mathematical certainty..."
- "This guarantee is cryptographically binding..."
- "Zero-knowledge proof of trustworthiness..."
- "Byzantine-resistant aggregation..."

### Why This Matters

Byzantine resilience and cryptographic proofs solve a different problem (protocol integrity) than operational safety assessment (empirical behavior monitoring).

### What We Actually Do

- Provide statistical confidence intervals (not mathematical proofs)
- Use well-understood anomaly detection techniques
- Generate evidence-based recommendations
- Enable human judgment with transparency

---

## ❌ We Do NOT Operate in Real-Time Streaming (By Default)

### What We Don't Do

- Process updates with microsecond latency
- Support <100ms decisioning for safety-critical systems (by default)
- Handle unbounded message throughput

### Why This Matters

Our baseline is designed for batch/batch-like federated learning systems (updates aggregated daily/weekly). Real-time streaming requires architectural choices we don't make by default.

### What We Actually Do

- Support streaming with <500ms latency per update
- Allow deployment on edge hardware for real-time use cases (with tuning)
- Scale to 10,000+ updates/day in batch mode
- Support async monitoring for high-frequency updates

### Known Limitation

Autonomous vehicle systems requiring <100ms per-update decisions need engineering for deployment (possible, but not baseline).

---

## ❌ We Do NOT Identify Which Participant Is Responsible

### What We Don't Do

- "Participant-42 is poisoning the model"
- Attribute model degradation to specific participants
- Rank participants by trustworthiness score
- Create participant reputation scores

### Why This Matters

In consortium scenarios, attribution can create liability and broken trust. In privacy-first systems, we shouldn't enable participant identification.

### What We Actually Do

- "Update #5284 is anomalous" (identify the update, not the participant)
- "This class of updates shows pattern X" (behavioral observation)
- In identified systems (hospital networks): Participant information available for review
- In anonymous systems (consortiums): Keep updates unidentified

---

## ❌ We Do NOT Replace Human Oversight

### What We Don't Claim

- "You don't need to review flagged updates"
- "Our system makes all the decisions"
- "Hands-off governance is possible"
- "Experts aren't needed"

### Why This Matters

Federated learning involves business relationships, legal obligations, and safety-critical decisions. Humans must retain authority.

### What We Actually Do

- Automate routine decisions (updates that clearly pass/fail checks)
- Flag edge cases for expert review
- Provide interface for human override
- Document rationale for every decision

**Design principle:** Humans decide policy; our system implements policy.

---

## ❌ We Do NOT Solve Byzantine Resilience

### What We Don't Do

- Guarantee safety under coordinated majority attack
- Provide Byzantine-resistant aggregation
- Implement secure multi-party computation
- Solve consensus in adversarial settings

### Why This Matters

Byzantine resilience (handling f out of n malicious participants simultaneously) is a different problem with different solutions (e.g., Krum, Multi-Krum, RONI).

### What We Actually Do

- Complement Byzantine-resilient aggregation (orthogonal layer)
- Flag participants whose updates consistently cause problems
- Provide evidence for decisions to remove participants (Byzantine resilience handles how)
- Work alongside Byzantine-resistant algorithms

---

## ❌ We Do NOT Guarantee Interpretability

### What We Don't Claim

- "Every decision is 100% interpretable to a layperson"
- "No machine learning involved"
- "Our logic is trivial to understand"

### Why This Matters

Trust assessment combines statistical signals, historical data, and domain knowledge. Perfect transparency is impossible.

### What We Actually Do

- Explain decisions in terms of evidence (not black-box scoring)
- Show which signals contributed to each decision
- Use interpretable methods (anomaly scores, statistical thresholds)
- Provide detailed audit logs for expert review

**Design principle:** Interpretable-by-experts > black-box-to-everyone

---

## ❌ We Do NOT Work Without Any Metadata

### What We Don't Do

- Make decisions on model parameters alone (without any context)
- Evaluate updates in isolation from history
- Work in a vacuum (no participant history available)

### Why This Matters

Our approach depends on behavioral signals. We need:
- Historical track record of participant
- Metadata about update (training set size, validation metrics)
- Context about global model (baseline for comparison)

### What We Actually Do

- Require minimal metadata (not raw data)
- Work with incomplete history (gracefully degrade confidence)
- Bootstrap new participants with default policies
- Accumulate signal over time

---

## ❌ We Do NOT Provide Liability Protection

### What We Don't Do

- Guarantee that accepting our recommendations is safe
- Indemnify you if something goes wrong
- Accept legal liability for your decisions
- Replace due diligence requirements

### Why This Matters

Organizational decisions about model deployment carry liability. Our role is to inform, not absolve responsibility.

### What We Actually Do

- Provide evidence trails for informed decision-making
- Document decision rationale for liability defense
- Enable organizations to claim "due diligence in governance"
- Support experts in making defensible decisions

**Design principle:** We enable accountability, not avoid it.

---

## ❌ We Do NOT Enforce Data Privacy

### What We Don't Do

- Guarantee GDPR, HIPAA, CCPA compliance
- Prevent data breaches
- Audit data handling practices
- Verify informed consent

### Why This Matters

Privacy is enforced by federation architecture and legal/organizational policy, not by trust assessment.

### What We Actually Do

- Respect federated learning privacy by design (never request raw data)
- Work compatibly with privacy-preserving technologies (differential privacy, secure aggregation)
- Provide audit logs for privacy compliance reviews
- Enable privacy-first governance

---

## ❌ We Do NOT Solve Data Quality At Source

### What We Don't Do

- Improve participant training practices
- Teach better data collection
- Enforce data standards
- Prevent garbage in the first place

### Why This Matters

Prevention is better than detection, but Protector Uttam assumes we can't control the source.

### What We Actually Do

- Observe data quality signals from model behavior
- Flag when quality degrades
- Provide feedback to participants
- Enable governance that incentivizes quality

---

## What This Leaves Us With

### The Scope We Accept

✅ **Operational risk assessment** (not trustworthiness proof)
✅ **Evidence-based decision support** (not policy enforcement)
✅ **Scalable monitoring** (not manual expert replacement)
✅ **Audit trails** (not legal compliance guarantee)
✅ **Anomaly detection** (not adversarial attack immunity)
✅ **Transparency** (not perfect interpretability)
✅ **Privacy-compatible** (not privacy enforcement)

### The Philosophy

**We are honest about our limitations.**

We don't claim to solve harder problems than we do. We don't promise certainty where only evidence exists. We don't replace human judgment; we enable it.

This honesty is our strength. Customers can trust us precisely because we're clear about what we can't do.

---

**Next:** See [ASSUMPTIONS.md](ASSUMPTIONS.md) for core assumptions underlying this product.
