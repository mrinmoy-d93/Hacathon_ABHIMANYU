# 🔍 KHOJO — AI-Powered Missing Person Finder

<div align="center">

![Version](https://img.shields.io/badge/FRS-v1.1-blue)
![Status](https://img.shields.io/badge/Status-Final-green)
![Hackathon](https://img.shields.io/badge/Amnex%20Hackathon-2026-orange)
![Use Case](https://img.shields.io/badge/UC34-Missing%20Person%20Finder-red)
![Domain](https://img.shields.io/badge/Domain-Social%20Impact-purple)

**"AI suggests, the human decides."**

*An Artificial Intelligence (AI) powered mobile and web solution to locate missing persons through facial aging prediction and age-invariant face recognition.*

</div>

---

## 🚨 The Problem

India records **100,000+ missing person cases every year**. Nearly 45% of these are children who go missing at a young age — and when sighted years later, are completely unrecognisable due to natural aging.

> A 10-year-old child missing in 2009 would appear as a **27-year-old adult in 2026** — a face no photograph in the case file resembles.

| Metric | Figure |
|--------|--------|
| Missing persons / year | 1,00,000+ |
| Children as % of missing | ~45% |
| Cases solved within 1 year | ~30% |
| Average duration of search | 3–7 years |

KHOJO bridges this visual gap using AI to predict how a missing person looks **today**, and automatically matches that prediction against a growing database of sighted individuals.

---

## ✨ What KHOJO Does

- 📸 **Accepts old photographs** of a missing person (minimum 2, tagged with age at capture)
- 🧠 **Predicts present-day appearance** using a Generative Adversarial Network (GAN) trained on facial aging
- 🔎 **Matches the aged face** against a sightings database using age-invariant face recognition
- 📊 **Scores each match** with a calibrated confidence score and routes alerts accordingly
- 🔁 **Learns continuously** from field worker feedback to improve over time

---

## 🏗️ System Architecture

```
[ PRESENTATION LAYER ]
  React Native Mobile App (iOS + Android)  |  React Web Admin Console

[ API GATEWAY ]
  FastAPI — REST Endpoints  |  JWT Authentication  |  Rate Limiter  |  Circuit Breaker

[ AI PROCESSING ENGINE ]  ← fully local, no biometric data sent externally
  InsightFace (Detection + Landmarking)
    → ArcFace (Embedding)
    → Aging Trajectory Module
    → SAM / HRFAE GAN (Age Progression)
    → ArcFace Cosine Similarity (Recognition)
    → Confidence Scorer
    → Alert Router

[ DATA LAYER ]
  PostgreSQL (Cases, Users, Audit Log)
  Redis (Job Queue, Session)
  MinIO / S3-compatible (Images, encrypted at rest)

[ OPTIONAL EXTERNAL ]
  OpenAI GPT-4o (Case Summaries + Alert Messages only)
  GeoPy Geocoding
```

> **Privacy Principle:** All computer vision processing runs **locally on-premise**. No biometric data is ever transmitted to external services.

---

## 🤖 AI Pipeline

| Step | Operation | Technology | Output |
|------|-----------|------------|--------|
| 1 | Face Detection | InsightFace / RetinaFace | Bounding box + 68-point landmark map |
| 2 | Face Embedding | ArcFace (ResNet-50, MS1MV3) | 512-d L2-normalised vector |
| 3 | Aging Trajectory | Custom Python module | Per-dimension aging rate ∆v |
| 4 | Age Progression | SAM / HRFAE GAN (PyTorch) | Aged RGB image at predicted age |
| 5 | Target Embedding | ArcFace | 512-d target embedding |
| 6 | DB Search | pgvector (IVFFlat index) | Ranked top-K candidates |
| 7 | Confidence Score | Sigmoid-calibrated cosine similarity | Score in [0, 1] + tier label |
| 8 | Alert Routing | FastAPI + Firebase FCM | Push alert or review queue entry |
| 9 | Summary (optional) | OpenAI GPT-4o | Plain-language summary |
| 10 | Audit Log | PostgreSQL (append-only, SHA-256 chained) | Tamper-evident audit record |

### Confidence Tiers

| Score | Tier | Action |
|-------|------|--------|
| ≥ 80% | 🟢 High | Immediate push notification to assigned field worker |
| 60–80% | 🟡 Medium | Queued for mandatory human review |
| < 60% | 🔴 Low | Marked inconclusive, stored for manual review |

---

## 🧰 Technology Stack

| Layer | Technology |
|-------|-----------|
| Mobile App | React Native 0.73+ (Expo) — iOS & Android |
| Backend API | Python 3.11 + FastAPI |
| Task Queue | Celery 5 + Redis 7 |
| Face Detection | InsightFace 0.7 (RetinaFace) |
| Face Recognition | ArcFace ResNet-50 (MS1MV3) |
| Face Aging GAN | SAM / HRFAE (PyTorch 2.x) |
| Vector Database | PostgreSQL 15 + pgvector 0.6 (IVFFlat) |
| Primary Database | PostgreSQL 15 |
| Object Storage | MinIO (S3-compatible, AES-256 at rest) |
| Caching / Session | Redis 7 |
| Geocoding | GeoPy + Nominatim (local instance) |
| AI Summaries | OpenAI GPT-4o (optional) |
| Push Notifications | Firebase Cloud Messaging (FCM) |
| API Gateway | Nginx 1.25 (TLS 1.3 termination) |
| Deployment | Docker Compose |

---

## 👥 User Roles

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| 👨‍👩‍👧 Community / Family | Citizen with a missing relative or a witness | Register case, upload photos, view match results |
| 🦺 Field Worker | NGO representative or constable | Receive alerts, verify matches, upload sightings, submit feedback |
| 🏛️ Administrator | Government officer / senior police | Full access + threshold tuning, audit export, field worker management |
| 🤖 System (AI) | Fully automated | Run AI pipeline, compute confidence, dispatch alerts, log decisions |

---

## 📱 Key Features

### For Families & Community
- Register a missing person case with photos and basic details
- System auto-computes **Predicted Present-Day Age** = Age at Disappearance + (Current Year − Year of Disappearance)
- Receive SMS + in-app notification when a match is found
- Track case status via unique reference ID (format: `KHJ-YYYY-XXXXX`)

### For Field Workers
- Receive high-priority push alerts for high/medium confidence matches
- View side-by-side: original photo, AI-aged prediction, candidate sighting
- Submit **Confirm Match** or **Not a Match** (with mandatory photo upload)
- Feed directly improves the AI model over time

### For Administrators
- **Overview Dashboard** — live counts, confidence distribution chart, geo-heatmap
- **Case Management** — filter, approve, reject cases
- **Field Worker Management** — zone assignment, accuracy scores, leave management
- **AI Settings** — no-code threshold tuning via sliders and toggles
- **Audit Log** — cryptographically chained, tamper-evident, CSV exportable

---

## 🔐 Security & Privacy

- **OTP authentication** (6-digit, 5-minute expiry, rate-limited)
- **2FA for administrators** — OTP + hashed government ID (bcrypt, cost 12)
- **JWT tokens** expire after 24 hours; refresh tokens after 30 days
- **RBAC** — community_member < field_worker < administrator
- **Zero biometric data** sent to any external API
- **Phone numbers and government IDs** stored only as bcrypt hashes
- **AES-256 encryption** at rest for all images
- **TLS 1.3** for all data in transit
- **Tamper-evident audit chain** — SHA-256 chained checksums on every log entry

---

## 🔁 Continuous Learning Loop

When a field worker submits "Not a Match" with an actual photo:

1. ArcFace compares the AI prediction against the real photograph
2. Per-feature error vector computed across: nose shape, cheekbones, jawline, eye spacing, forehead width, chin shape
3. Error vector stored in `training_pool` table
4. When **50 examples** accumulate → automatic model fine-tune triggered
5. Model version incremented (e.g., `v1.0 → v2.0`)
6. Family notified, case reopened

> This progressively adapts the global GAN to **South Asian facial aging characteristics** without requiring a bespoke training dataset.

---

## 🚀 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | None | Register a new user |
| POST | `/auth/otp/verify` | None | Verify OTP, get session token |
| POST | `/cases` | JWT | Create a missing person case |
| POST | `/cases/{id}/photos` | JWT | Upload photographs |
| POST | `/cases/{id}/process` | JWT | Trigger AI pipeline |
| GET | `/jobs/{job_id}` | JWT | Poll job status and result |
| POST | `/sightings` | JWT (field worker) | Submit a sighting report |
| POST | `/matches/{id}/confirm` | JWT (field worker) | Confirm a match |
| POST | `/matches/{id}/not-a-match` | JWT (field worker) | Submit Not a Match + photo |
| GET | `/admin/dashboard` | JWT (admin) | Real-time overview stats |
| PUT | `/admin/settings` | JWT (admin) | Update AI thresholds |
| GET | `/admin/audit-log` | JWT (admin) | Tamper-evident audit log |
| GET | `/health` | None | Service health check |

---

## ✅ Acceptance Criteria

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| AC-1 | End-to-end flow | New user completes input → result without external instructions |
| AC-2 | Aging speed | Face-aging output produced within **3 seconds** |
| AC-3 | Confidence display | Every decision shows a numerical score + plain-language explanation |
| AC-4 | Fallback path | Score < 0.60 triggers human review, never an unvetted answer |
| AC-5 | Audit log | Every AI invocation written with timestamp, hashes, model version |
| AC-6 | Stability | Backend runs 15-minute demo without crashes or memory leaks |
| AC-7 | Acronym expansion | All domain acronyms expanded at first occurrence on each screen |
| AC-8 | Graceful errors | External API failure degrades gracefully with a user message |
| AC-9 | Feedback loop | Not-a-Match updates training_pool; fine-tune triggers at 50 samples |
| AC-10 | Age formula | Predicted age computed correctly for any valid input |
| AC-11 | 2FA | Admin login requires both OTP and government ID |
| AC-12 | Tamper-evident audit | Tampered audit entries detectable via SHA-256 chain verification |

---

## ⚡ Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | End-to-end flow < **5 seconds**; aging module alone < **3 seconds** |
| Scalability | Horizontal Docker scaling; pgvector sub-second search at 1M embeddings |
| Security | TLS 1.3 in transit; AES-256 at rest; append-only tamper-evident audit |
| Reliability | Exponential backoff (3 retries); circuit-breaker (5 failures → open) |
| Observability | Structured JSON logs; `GET /health` responds in < 200 ms |

---

## 🔮 Future Enhancements

- Integration with **CCTNS** (Crime and Criminal Tracking Network and Systems)
- **Multilingual support** — Hindi, Gujarati, Marathi, Tamil, Bengali, Telugu
- **Edge deployment** on field-worker devices for offline verification
- **WhatsApp chatbot** for case registration without a smartphone app
- **Federated learning** across states — improve model without centralising biometric data
- **CCTV feed integration** at railway stations and bus terminals
- **Aadhaar-linked verification** pathway (subject to regulatory approval)

---

## ⚠️ Disclaimer

> *"This is an estimate produced by Artificial Intelligence (AI). Please have the result verified by a certified officer before acting upon it."*

Every AI-generated result in KHOJO is a **recommendation to a human being, never a final verdict**. Every match must be physically verified before a family is informed. Every mistake becomes training data for the next iteration of the model.

---

## 📄 Documentation

- [Functional Requirements Specification (FRS) v1.1](./KHOJO_FRS_Detailed_v1_1.pdf)

---

## 📋 Project Info

| Field | Detail |
|-------|--------|
| Hackathon | Amnex Hackathon 2026 |
| Use Case | UC34 — Missing Person Finder |
| Domain | Social Impact |
| FRS Version | 1.1 (Detailed Edition) |
| Date | 24 April 2026 |
| Team | KHOJO |

---

<div align="center">
Made with ❤️ for social impact &nbsp;|&nbsp; Team KHOJO &nbsp;|&nbsp; Amnex Hackathon 2026
</div>
