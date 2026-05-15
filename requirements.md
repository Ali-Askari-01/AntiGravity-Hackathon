# System Requirements & Progress Tracking

## Core Agents Overview

- [x] **Agent 0: Munsif (Orchestrator)**
  - Master coordinator — routes, retries, maintains session state.
  - Receives raw user input. Calls agents in sequence: Zuban -> Khoji -> Jadwal -> Qeemat -> Hukum.
  - On any agent failure, decides: retry / ask user / trigger fallback.
  - Maintains full session JSON. Its trace log is the "workplan".

- [x] **Agent 1: Zuban (Intent Agent)**
  - Multilingual NLP — all languages, confidence scoring.
  - Parses Urdu, Roman Urdu, English, mixed, misspelled input.
  - Returns intent JSON with confidence score (0-1).
  - If confidence <0.75: generates ONE clarifying question.
  - Classifies job as basic / intermediate / complex.
  - Detects urgency level (normal / urgent / emergency).

- [x] **Agent 2: Khoji (Matching Agent)**
  - Advanced provider matching (6+ factors).
  - Skill + job complexity classification.

- [x] **Agent 3: Jadwal (Scheduling Agent)**
  - Scheduling intelligence (double booking, buffers, waitlists).

- [x] **Agent 4: Qeemat (Pricing Agent)**
  - Dynamic pricing (demand, urgency, distance, surge, loyalty).

- [x] **Agent 5: Hukum (Booking Agent)**
  - Booking simulation (confirmation, receipt, DB write, notification).

- [x] **Agent 6: Mayaar (Quality Agent)**
  - Service quality loop (en-route, completion, feedback, rating impact).

- [x] **Agent 7: Insaf (Dispute Agent)**
  - Dispute + escalation (all types: no-show, price, quality, overrun).

- [x] **Agent 8: Bonus Agent (Provider Optimization)**
  - Provider-side optimization (workload, demand forecast, time slots).

## Coverage Map Requirements

- [x] 1. Multilingual + noisy input (Zuban)
- [x] 2. Advanced provider matching (Khoji)
- [x] 3. Skill + job complexity classification (Khoji)
- [x] 4. Scheduling intelligence (Jadwal)
- [x] 5. Dynamic pricing (Qeemat)
- [x] 6. Booking simulation (Hukum)
- [x] 7. Service quality loop (Mayaar)
- [x] 8. Dispute + escalation (Insaf)
- [x] 9. Provider-side optimization (Bonus)
- [x] 10. Robustness + fallback (All Agents / Munsif)
