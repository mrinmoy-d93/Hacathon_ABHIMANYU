# Functional Requirements Specification (FRS)

## KHOJO — Artificial Intelligence (AI) Powered Missing Person Finder with Facial Aging Technology

---

| Field | Detail |
|---|---|
| **Project Name** | KHOJO |
| **Hackathon** | Amnex Hackathon 2026 |
| **Use Case Reference** | UC34 — Missing Person Finder |
| **Domain** | Social Impact |
| **Category** | General |
| **Primary Modules** | Mobile Application, Application Programming Interface (API), Admin Console |
| **Complexity** | High |
| **Document Type** | Functional Requirements Specification (FRS) |
| **Version** | 1.0 |
| **Date** | 24 April 2026 |
| **Status** | Final — Submitted |

### Document Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 0.1 | 22 April 2026 | Team KHOJO | Initial draft |
| 0.2 | 23 April 2026 | Team KHOJO | Internal review and corrections |
| 1.0 | 24 April 2026 | Team KHOJO | Final version for hackathon submission |

---

## Table of Contents

1. Introduction
2. Problem Statement
3. Scope of the Solution
4. Definitions, Acronyms, and Abbreviations
5. System Overview
6. Users and Roles (Actors)
7. Functional Requirements
8. User Flows
9. Artificial Intelligence (AI) Pipeline — Technical Summary
10. Non-Functional Requirements
11. Technology Stack
12. External Integrations and Data Sources
13. Audit, Logging, and Compliance
14. Administrator Controls
15. Performance and Deployment
16. Acceptance Criteria
17. Assumptions and Dependencies
18. Risks and Mitigations
19. Future Enhancements
20. Glossary

---

## 1. Introduction

### 1.1 Purpose

This Functional Requirements Specification (FRS) document describes the complete functional behaviour, user interactions, technical architecture, and acceptance criteria of **KHOJO** — an Artificial Intelligence (AI) powered mobile and web solution designed to locate missing persons through facial aging prediction and age-invariant face recognition.

The document is intended to serve as the authoritative reference for the development team, judges, reviewers, and future maintainers of the system.

### 1.2 Intended Audience

- Hackathon judges and evaluation panel
- Project developers and testers
- Domain experts from law enforcement and non-governmental organisations
- Government officers responsible for missing person cases
- Future contributors to the open-source repository

### 1.3 Document Conventions

- The terms "must", "shall", and "required" denote mandatory requirements.
- The terms "should" and "recommended" denote preferred but non-mandatory requirements.
- All technical acronyms are expanded at first occurrence in each section.

---

## 2. Problem Statement

India records more than one hundred thousand (100,000+) missing person cases every year. A significant proportion of these are children who go missing at an early age and, when eventually found or sighted, are no longer recognisable because their facial features have changed considerably due to aging. Families, shelter homes, and law-enforcement officers lack a reliable tool to bridge this visual gap between the last known photograph and the present-day appearance of the missing individual.

**KHOJO** addresses this problem by applying Artificial Intelligence (AI) to predict how a missing person is likely to appear today, based on one or more older photographs, and by automatically matching this predicted face against a database of sighted and registered individuals.

---

## 3. Scope of the Solution

The solution is delivered as three tightly integrated components:

1. **Mobile Application** — used by community members, family members of missing persons, and field workers.
2. **Backend Application Programming Interface (API)** — the processing layer that performs face detection, embedding, aging, recognition, scoring, and alert routing.
3. **Administrator Console** — a role-based interface used by government officers and police to manage cases, field workers, thresholds, and audit logs.

The scope includes end-to-end case registration, AI-driven age progression, match detection, human-in-the-loop verification, a "Not a Match" continuous-learning feedback loop, alerting, and tamper-evident auditing.

---

## 4. Definitions, Acronyms, and Abbreviations

| Term | Expansion / Meaning |
|---|---|
| AI | Artificial Intelligence |
| ML | Machine Learning |
| API | Application Programming Interface |
| FRS | Functional Requirements Specification |
| GAN | Generative Adversarial Network |
| GPT-4o | OpenAI's multimodal Generative Pre-trained Transformer, version 4 Omni |
| HRFAE | High-Resolution Face Age Editing — a published face-aging model |
| SAM | Style-based Age Manipulation (a published face-aging model) |
| ArcFace | A deep face-recognition model that produces angular-margin embeddings |
| InsightFace | An open-source face analysis toolkit used for detection and landmarking |
| PII | Personally Identifiable Information |
| OTP | One-Time Password |
| CSV | Comma-Separated Values |
| NGO | Non-Governmental Organisation |
| PoC | Proof of Concept |

---

## 5. System Overview

KHOJO operates on the core principle: **"AI suggests, the human decides."**

The system ingests one or more historical photographs of a missing person, predicts the present-day appearance using a face-aging Generative Adversarial Network (GAN), and searches a growing database of sighted individuals using age-invariant face recognition. Every decision is accompanied by a confidence score and a plain-language explanation, and no match is considered final until it has been physically verified by an authorised field worker.

A distinctive feature of KHOJO is its **"Not a Match" feedback loop**, which captures the real photograph of any incorrectly matched individual, derives an error vector between the AI prediction and the actual face, and feeds this into a continuous-learning pool. Over time this tunes the generic global model into one that is specifically suited to the Indian subcontinent, without requiring a dedicated training dataset.

---

## 6. Users and Roles (Actors)

| Actor | Description | Key Responsibilities |
|---|---|---|
| **Community Member / Family** | An ordinary citizen who has a missing relative or who wishes to report an unknown sighted person. | Registers missing person cases, uploads photographs, views AI-generated results and match status. |
| **Field Worker** | An NGO representative or police officer operating in the field. | Visits shelter homes, hospitals, and other locations; verifies potential matches physically; uploads photographs of sighted individuals; submits feedback. |
| **Administrator** | A government officer or senior police official. | Approves or rejects cases; tunes AI thresholds; manages field workers; exports audit logs; monitors overall system health. |
| **System (AI, Automated)** | No human involvement — fully automated. | Performs face detection, embedding, aging, recognition, scoring, alert routing, and summary generation. |

---

## 7. Functional Requirements

### 7.1 Input, Registration, and Onboarding

- **FR-1.1** The mobile application must allow every user to register using name, phone number, and location, and to select their role (Family Member, Community Member, Field Worker, or Administrator).
- **FR-1.2** Authentication must be performed through a One-Time Password (OTP) sent to the registered mobile number. Administrators must additionally authenticate using a police/government identification number (two-factor authentication).
- **FR-1.3** The mobile application must confirm successful submission of any case or verification with a clear on-screen acknowledgement and a unique reference identifier in the format **KHJ-YYYY-XXXXX**.
- **FR-1.4** Input validation must reject malformed or out-of-range data (for example, future years, invalid ages, unreadable images) with a plain-language error message.

### 7.2 Missing Person Case Registration

- **FR-2.1** The user must be able to enter the missing person's name, the year the person went missing, the age at which the person went missing, and the last known location (city or area).
- **FR-2.2** The system must automatically compute the predicted present-day age using the following formula and display it as a read-only field:

  > **Predicted Present-Day Age = Age at Disappearance + (Current Year − Year of Disappearance)**

  *Example:* If a person went missing in 2009 at the age of 10, the system must display: `10 + (2026 − 2009) = 27 years`.

- **FR-2.3** The user must be required to upload a **minimum of two (2) photographs**, each tagged with the age of the person at the time the photograph was taken. Additional photographs (third, fourth, and beyond) may be uploaded to improve accuracy.
- **FR-2.4** The user should optionally provide identifying marks (moles, scars, marks near the eye, etc.) in a free-text field.

> **Rationale for requiring two photographs:** A minimum of two photographs allows the AI to learn the individual's unique aging trajectory between the two known ages, and then extrapolate that trajectory forward to the predicted present-day age. This yields measurably higher accuracy than single-photograph age progression.

### 7.3 Core Artificial Intelligence Processing

The backend must implement the following AI capabilities as distinct, independently testable modules:

- **FR-3.1 Face Detection.** Using InsightFace, each uploaded photograph must be analysed to detect a single primary face and mark 68 facial landmark key points.
- **FR-3.2 Face Embedding.** Using ArcFace, each detected face must be converted into a 512-dimensional numerical embedding (the "face fingerprint").
- **FR-3.3 Aging Trajectory Calculation.** A custom module must compute the aging trajectory from the set of embeddings, each tagged with the known age.
- **FR-3.4 Face Aging Generation.** Using a Style-based Age Manipulation (SAM) or High-Resolution Face Age Editing (HRFAE) Generative Adversarial Network (GAN), the system must generate an aged photograph of the person at the predicted present-day age.
- **FR-3.5 Age-Invariant Recognition.** The aged embedding must be compared against every embedding in the database of sighted/registered individuals using ArcFace cosine similarity.
- **FR-3.6 Confidence Scoring.** Every match must produce a confidence score in the range 0.0 to 1.0.
- **FR-3.7 Alert Routing.** Based on configurable thresholds, the system must automatically dispatch a field-worker alert, queue the case for human review, or flag it as inconclusive.
- **FR-3.8 Geo-Spatial Clustering.** Using GeoPy for geocoding, the system must identify zones where three or more sightings or cases cluster, and raise a geo-alert to the administrator.
- **FR-3.9 Summary Generation (optional).** When enabled, GPT-4o must generate a concise case summary for investigators and a community-facing alert message. Every GPT-4o invocation must include a deterministic system prompt version identifier so that responses are reproducible and auditable.

### 7.4 Output and User Experience

- **FR-4.1** The mobile application must present every AI-generated result on a clearly labelled screen that shows the original photographs side-by-side with the AI-generated aged photograph.
- **FR-4.2** Every AI-generated decision must include a visible confidence score (displayed both numerically and as a bar) and a plain-language explanation of how the result was derived.
- **FR-4.3** The result screen must classify the outcome into one of three tiers:

  | Confidence Score | Tier | System Action |
  |---|---|---|
  | ≥ 80% | High confidence | Automatic alert dispatched to the assigned field worker. |
  | 60% – 80% | Medium confidence | Case queued for mandatory human review. |
  | < 60% | Low confidence | Marked inconclusive; manual verification required. |

- **FR-4.4** A plain-language disclaimer must always appear on the result screen:

  > *"This is an estimate produced by Artificial Intelligence. Please have the result verified by a certified officer before acting upon it."*

- **FR-4.5** A unique Case Identifier in the format `KHJ-2026-XXXXX` must be generated and displayed on the result screen.

### 7.5 Field Worker Flow — Verification and Feedback

- **FR-5.1** Field workers must receive in-app alerts for potential matches, showing the predicted aged photograph alongside the candidate photograph with location and confidence score.
- **FR-5.2** After physical verification, the field worker must be able to mark the case as either **"Confirm Match"** or **"Not a Match"**.
- **FR-5.3** On confirming a match, the system must automatically notify the registered family member using a message composed by GPT-4o (when enabled) or a standard template (when GPT-4o is disabled).
- **FR-5.4** On marking "Not a Match", the field worker **must mandatorily upload the actual photograph of the individual encountered** at the location. The system must refuse to accept the "Not a Match" submission without this photograph.
- **FR-5.5** On receiving a "Not a Match" feedback, the backend must:
  1. Run feature-by-feature comparison between the AI-generated prediction and the uploaded real photograph (nose shape, cheekbone structure, jawline, eye spacing, etc.).
  2. Compute a per-feature error vector.
  3. Append the error vector to a training pool for continuous learning.
  4. Trigger a model fine-tune cycle when the training pool accumulates fifty (50) such examples, advancing the model version (for example, from v1.0 to v2.0).
  5. Notify the original family member that the match was not confirmed and that the case remains active.
  6. Automatically reopen the case.

### 7.6 Administrator Controls

The administrator console must provide the following five tabs:

#### 7.6.1 Tab 1 — Overview Dashboard
- Live counts of total cases, active searches, matches found, and cases pending human review.
- AI confidence distribution chart with three bars: High (≥80%, green), Medium (60–80%, amber), Low (<60%, red).
- Real-time recent activity feed.

#### 7.6.2 Tab 2 — Case Management
- Filter by status (All / Review Pending / Found / Closed).
- Each case must display name, Case Identifier, predicted age, match location, and confidence score.
- Administrators must be able to **Approve** (dispatches field-worker alert) or **Reject** (closes case and notifies family).

#### 7.6.3 Tab 3 — Field Worker Management
- List of all field workers with zone assignment, verification count, and personal accuracy score.
- Ability to add, reassign, or remove a field worker.
- Leave-status management.

#### 7.6.4 Tab 4 — AI Settings (No-Code)
- **Confidence Threshold** slider: 40% to 90% (default 60%).
- **Auto-Alert Threshold** slider: 60% to 99% (default 80%).
- **GPT-4o Summaries** toggle: On / Off.
- **Geo-Clustering Alerts** toggle: On / Off (alert when three or more cases cluster in one zone).
- Display of the currently deployed AI model version.

#### 7.6.5 Tab 5 — Audit Log
- Every AI decision must be recorded with timestamp, model version, action taken, confidence score, and outcome.
- Logs must be tamper-evident — every entry cryptographically signed, and edits or deletions disallowed.
- CSV export must be available for any selected date range.
- Personally Identifiable Information (PII) must be redacted from logs, except where retention is legally required.

---

## 8. User Flows

### 8.1 Community Member Flow

1. **Register / Login** — the user enters name, phone number, and location; selects role; and verifies via OTP.
2. **Missing Person Details** — the user enters the name, year of disappearance, age at disappearance, and last known location. The system auto-calculates and displays the predicted present-day age.
3. **Photo Upload** — the user uploads at least two photographs, each tagged with the age of the person at the time of capture. Optionally, identifying marks may be entered.
4. **AI Processing (automatic)** — the backend performs face detection, embedding, aging, recognition, scoring, and alert routing; all steps are written to the audit log.
5. **Result** — the user sees original photographs alongside the AI-generated aged photograph, the confidence score, the tier classification, the plain-language disclaimer, and the Case Identifier.

### 8.2 Field Worker Flow — Normal Path (Match Confirmed)

1. An in-app alert arrives, for example: *"Possible match — Surat Shelter Home, 78% confidence."*
2. The predicted aged photograph and the candidate photograph are displayed side-by-side.
3. The field worker physically visits the shelter.
4. On positive verification, the field worker taps **Confirm Match**.
5. The registered family member receives an automatic notification, composed by GPT-4o when enabled.

### 8.3 Field Worker Flow — Alternate Path ("Not a Match" Feedback Loop)

> *Illustrative scenario:* Anita Ben (field worker) visits a shelter where an 80% match was flagged. The girl at the shelter is clearly not the missing person.

1. The field worker taps **Not a Match**.
2. The field worker is required to upload the actual photograph of the encountered individual before submission is accepted.
3. The AI backend now holds two items: the AI-generated predicted face and the actual photograph.
4. The system performs feature-by-feature comparison and computes an error vector, for example:
   - Nose shape error: 0.23
   - Cheekbone error: 0.31
   - Jawline error: 0.18
5. The error vector is added to the continuous-learning pool.
6. After 50 such examples accumulate, the model is fine-tuned and the version advances (for example, v1.0 → v2.0).
7. The family member is notified that the match was not confirmed and that the case remains active.
8. The case is automatically reopened.

> **Strategic benefit:** The more the system is used in India, the more accurately it learns South-Asian facial aging characteristics — without requiring a bespoke training dataset. A generic global model gradually becomes an Indian-subcontinent-specific model through deployment itself.

### 8.4 Administrator Flow

1. The administrator logs in to the same mobile or web application and selects the Administrator role.
2. Two-factor authentication is performed (OTP plus police/government identification number).
3. The administrator navigates between the five tabs (Overview, Cases, Field Workers, AI Settings, Audit Log) to manage the system, approve or reject cases, tune thresholds without any code deployment, and export audit logs.

---

## 9. Artificial Intelligence (AI) Pipeline — Technical Summary

| Step | Operation | Technology |
|---|---|---|
| 1 | Face detection and 68-point landmarking on each input photograph | InsightFace |
| 2 | Generation of a 512-dimensional face embedding ("face fingerprint") | ArcFace |
| 3 | Aging trajectory calculation from the set of age-tagged embeddings | Custom module |
| 4 | Face aging generation at the predicted present-day age | SAM / HRFAE GAN |
| 5 | Age-invariant face recognition against the database | ArcFace cosine similarity |
| 6 | Confidence scoring (0.0 to 1.0) | ArcFace |
| 7 | Automatic alert routing or human-review queuing based on threshold | FastAPI backend |
| 8 | Case summary and community alert message (when enabled) | GPT-4o |
| 9 | Persistent audit logging of every decision | PostgreSQL |

---

## 10. Non-Functional Requirements

- **NFR-1 Performance.** The end-to-end primary-user flow must complete in under five (5) seconds for a typical input, excluding network latency to external APIs. The face-aging module alone must produce a measurable, testable output within three (3) seconds on a representative sample input.
- **NFR-2 Stability.** The backend must tolerate a representative dataset during a fifteen (15) minute demonstration run without crashes, memory leaks, or exceeding the stated hardware budget.
- **NFR-3 Graceful Degradation.** When any external API is temporarily unavailable, the flow must either degrade gracefully or fail with a user-understandable message. The user must never be left without a response.
- **NFR-4 Accessibility.** All user-facing text must expand AI, ML, API, and every other domain-specific acronym at its first occurrence on each screen.
- **NFR-5 Reliability.** Every external API call must implement retry with exponential backoff and a circuit-breaker so that a failing dependency cannot bring down the entire flow.
- **NFR-6 Security and Privacy.** PII must be redacted from all logs except where legal retention is required. Audit entries must be cryptographically signed and tamper-evident.
- **NFR-7 Scalability.** The system architecture must support horizontal scaling to handle nation-scale case volumes.

---

## 11. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Mobile Application | React Native | Cross-platform Android and iOS client |
| Backend | Python (FastAPI) | API server and business logic |
| Database | PostgreSQL | Persistence of cases, users, and audit logs |
| Face Recognition | InsightFace / ArcFace | Detection, landmarking, embedding, recognition (~500 MB) |
| Face Aging | SAM / HRFAE GAN | Age-progression generation (~1–2 GB) |
| AI Summaries (optional) | OpenAI GPT-4o API | Case summaries and community alert messages |
| Geocoding | GeoPy | Location resolution and clustering |
| Deployment | Docker Compose | Standard entry-point via `docker-compose.prod.yml` |

---

## 12. External Integrations and Data Sources

- **External APIs.** None. All Computer Vision processing is performed locally; only the optional GPT-4o summary generation calls an external API.
- **Pre-trained models and datasets.**
  - InsightFace / ArcFace for recognition (~500 MB).
  - SAM / HRFAE Generative Adversarial Network for face aging (~1–2 GB).
  - GeoPy for geocoding.
- **Sample data.** Sample face images at varying ages must be supplied in the repository for testing and demonstration purposes.

---

## 13. Audit, Logging, and Compliance

- **AL-1** Every AI-generated decision must be logged with timestamp, input, output, model version, and confidence score.
- **AL-2** The audit log must be tamper-evident; this is achieved through append-only storage and cryptographic checksums on each entry.
- **AL-3** PII must be redacted from logs. The only exception is when data retention is legally mandated.
- **AL-4** The administrator must be able to export the audit log for any selected date range as a Comma-Separated Values (CSV) file.
- **AL-5** The audit log is the authoritative evidence base for any post-facto investigation into system behaviour.

---

## 14. Administrator Controls

Refer to Section 7.6 for the detailed breakdown of the five administrator tabs. In summary, the administrator must be able to:

1. Monitor overall volumes, confidence distribution, and error rates in real time.
2. Approve or reject individual cases.
3. Manage field workers and their zone assignments.
4. Tune AI thresholds (confidence, auto-alert, geo-clustering) without redeploying the backend.
5. Export the tamper-evident audit log for legal or compliance purposes.

---

## 15. Performance and Deployment

- The backend must be deployable via the standard `docker-compose.prod.yml` entry-point shared across the hackathon portal.
- The deployment must include health checks on each service and must restart any failed container automatically.
- A Graphics Processing Unit (GPU) is required for the face-aging GAN in production; the recognition pipeline may run on CPU in a fallback mode for demonstration purposes.

---

## 16. Acceptance Criteria

| # | Criterion | Pass Condition |
|---|---|---|
| AC-1 | End-to-end flow | A new user can complete the flow from input to AI-generated result in a single session, without any instructions beyond those visible on the user interface. |
| AC-2 | Face-aging speed | The face-aging module produces a measurable, testable output on a representative input within three seconds. |
| AC-3 | Confidence score | Every AI-generated decision is returned with a visible confidence score and a plain-language explanation. |
| AC-4 | Fallback path | A confidence score below the configurable threshold (default 0.60) triggers the documented fallback path — human review, alternative model, or a graceful "unable to determine" response — and never returns an unvetted answer. |
| AC-5 | Audit log | Every AI invocation is written to the audit log with timestamp, input, output, model version, and confidence score. |
| AC-6 | Stability | The backend runs a fifteen-minute demonstration on a representative dataset without crashes, memory leaks, or exceeding the stated hardware budget. |
| AC-7 | Acronym expansion | All user-facing text expands AI, ML, API, and any other domain-specific acronym at its first occurrence on each screen. |
| AC-8 | Graceful error handling | When any external API is temporarily unavailable, the flow degrades gracefully or fails with a user-understandable message. |
| AC-9 | "Not a Match" feedback loop | The field-worker "Not a Match" feedback, including the mandatory photograph upload, updates the training pool and triggers model fine-tuning after fifty samples. |
| AC-10 | Age formula correctness | The predicted present-day age is computed correctly as `Age at Disappearance + (Current Year − Year of Disappearance)`. |

---

## 17. Assumptions and Dependencies

- A reliable internet connection is available on the field worker's device at the time of verification.
- Users have a smartphone capable of running React Native applications.
- At least two usable photographs of the missing person are available from the family.
- The deployment host has access to a GPU of sufficient memory for the SAM / HRFAE model.
- GPT-4o API credits are available when summary generation is enabled.

---

## 18. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| False positive matches causing distress to families | Medium | High | Three-tier confidence classification, mandatory field-worker verification, plain-language disclaimer on every result. |
| Bias in the face-aging GAN towards non-Indian features | High (initially) | Medium | Continuous-learning feedback loop from "Not a Match" submissions progressively tunes the model to the Indian subcontinent. |
| External OpenAI API outage | Low | Low | GPT-4o summaries are optional; fallback to standard templates when unavailable. |
| Misuse of PII by unauthorised actors | Low | High | Two-factor authentication for administrators, PII redaction in logs, tamper-evident audit trail. |
| GPU resource unavailability | Medium | Medium | Demonstration fallback mode on CPU with documented performance expectations. |

---

## 19. Future Enhancements

- Integration with the Crime and Criminal Tracking Network and Systems (CCTNS) database.
- Multilingual support including Hindi, Gujarati, Marathi, Tamil, Bengali, and other Indian languages.
- Edge deployment on field-worker devices for offline verification in low-connectivity zones.
- WhatsApp chatbot for case registration by families who do not use smartphone applications.
- Federated learning across states to improve the model without centralising sensitive data.
- Integration with Closed-Circuit Television (CCTV) feeds at railway stations and bus terminals.

---

## 20. Glossary

| Term | Definition |
|---|---|
| **AI (Artificial Intelligence)** | A branch of computer science concerned with building systems that perform tasks that typically require human intelligence. |
| **API (Application Programming Interface)** | A defined contract that enables two software components to communicate. |
| **ArcFace** | A face-recognition loss function and model that produces angular-margin embeddings for highly discriminative face recognition. |
| **Embedding** | A numerical vector representation of data (in this system, a 512-dimensional vector representing a face). |
| **GAN (Generative Adversarial Network)** | A class of machine-learning framework in which two neural networks compete, used here to generate aged faces. |
| **GPT-4o** | OpenAI's multimodal (text, image, audio) version of Generative Pre-trained Transformer, version 4 Omni. |
| **HRFAE (High-Resolution Face Age Editing)** | A published face-aging model capable of producing high-resolution age-progressed images. |
| **InsightFace** | An open-source face-analysis toolkit used in this system for detection and landmarking. |
| **PII (Personally Identifiable Information)** | Any data that can identify an individual, directly or indirectly. |
| **SAM (Style-based Age Manipulation)** | A published face-aging model that manipulates age while preserving identity. In image-segmentation contexts, SAM may instead stand for Segment Anything Model — the meaning is context-dependent. |

---

## Closing Principle

> **"AI suggests, the human decides."**
>
> This principle is the foundation of the entire KHOJO system. Every AI-generated result is a recommendation to a human being, never a final verdict. Every match must be verified physically before a family is informed. Every mistake becomes training data for the next iteration of the model.

---

**— End of Functional Requirements Specification —**

*KHOJO — Amnex Hackathon 2026 | UC34 | FRS v1.0 | 24 April 2026*
