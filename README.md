# Policia — StrokeGuard AI

### AI-Assisted Ischemic Stroke Core & Penumbra Segmentation

**Developed for the Synapse Hackathon**

Policia, presented as **StrokeGuard AI**, is an AI-assisted research prototype for ischemic stroke imaging. The project combines a publicly available pretrained stroke-segmentation model with a full-stack application for **DICOM ingestion, segmentation-result processing, quantitative analysis, visualization, and clinician-oriented review**.

The system focuses on identifying two important regions in hyperacute ischemic stroke:

* **Ischemic Core** — tissue considered potentially irreversibly damaged
* **Ischemic Penumbra** — surrounding tissue that may still be salvageable

During the hackathon, we started with a publicly available pretrained baseline because of the limited development timeline and focused on improving the inference pipeline and building an end-to-end application around it.

> **Medical Disclaimer:** Policia is a research and hackathon prototype. It has not been clinically validated and must not be used independently for diagnosis, treatment decisions, or patient management.

---

## Table of Contents

* [Problem](#problem)
* [Solution](#solution)
* [System Workflow](#system-workflow)
* [Model](#model)
* [Inference Optimization](#inference-optimization)
* [Results](#results)
* [Application Architecture](#application-architecture)
* [Backend](#backend)
* [Frontend](#frontend)
* [DICOM Processing](#dicom-processing)
* [Segmentation Result Handling](#segmentation-result-handling)
* [Quantitative Analysis](#quantitative-analysis)
* [Authentication and Access Control](#authentication-and-access-control)
* [Mock Model Service](#mock-model-service)
* [Project Structure](#project-structure)
* [Technology Stack](#technology-stack)
* [Installation](#installation)
* [Running the Backend](#running-the-backend)
* [Running the Frontend](#running-the-frontend)
* [Current Status](#current-status)
* [Limitations](#limitations)
* [Future Improvements](#future-improvements)
* [Research Direction](#research-direction)
* [Acknowledgements](#acknowledgements)
* [References](#references)
* [Disclaimer](#disclaimer)

---

# Problem

Hyperacute ischemic stroke can be difficult to assess from **non-contrast CT (NCCT)** because early pathological changes can be subtle.

A useful AI-assisted system should not stop at segmentation. It should provide a complete workflow:

```text
Medical Image
      ↓
Preprocessing
      ↓
Segmentation
      ↓
Core + Penumbra Masks
      ↓
Quantitative Analysis
      ↓
Visualization
      ↓
Clinician Review
```

The challenge is particularly difficult because ischemic core and penumbra can be small, heterogeneous, and difficult to distinguish from normal anatomical variation and imaging artifacts.

For the Synapse Hackathon, our goal was to build a practical prototype around an existing pretrained stroke-segmentation model while improving its inference pipeline and providing an application layer for analysis and review.

---

# Solution

Policia combines a **pretrained segmentation model** with a full-stack system that handles the surrounding workflow.

The overall design is:

```text
                 ┌──────────────────────┐
                 │   DICOM Study / ZIP  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │    FastAPI Backend   │
                 │                      │
                 │ • Upload validation  │
                 │ • DICOM processing   │
                 │ • Slice ordering     │
                 │ • Authentication     │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Segmentation Model   │
                 │   (External Service) │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │      NPZ Result      │
                 │                      │
                 │ 0 → Background       │
                 │ 1 → Penumbra         │
                 │ 2 → Core             │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Result Validation &  │
                 │ Quantitative Analysis│
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Database + Storage   │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ StrokeGuard Dashboard│
                 │                      │
                 │ • Visualization      │
                 │ • Slice navigation  │
                 │ • Analysis display   │
                 │ • Report workflow    │
                 └──────────────────────┘
```

---

# System Workflow

The intended end-to-end workflow is:

### 1. Upload

A user uploads a compressed DICOM study.

### 2. Validate

The backend:

* checks the upload size
* safely extracts the archive
* validates DICOM files
* identifies valid slices
* orders slices using available DICOM spatial metadata

### 3. Segmentation

The backend communicates with a separate segmentation service through the `/predict` endpoint.

### 4. Result Validation

The returned NPZ file is validated to ensure that:

* the segmentation is three-dimensional
* the number of slices matches the input study
* the array contains integer labels
* only valid class labels are present

### 5. Quantitative Analysis

The system derives prototype core and penumbra measurements and calculates mismatch-related values.

### 6. Visualization

The results can then be consumed by the application layer for review and visualization.

---

# Model

The hackathon implementation started from a publicly available pretrained model associated with the **Early Hyperacute Stroke / CPAISD** research work.

The baseline research system uses an **FPN segmentation architecture with an EfficientNet-B0 backbone** and performs three-class segmentation:

```text
0 → Background
1 → Penumbra
2 → Ischemic Core
```

The original pretrained model is **not bundled directly inside this repository**.

Instead, Policia treats the segmentation model as an external service. This keeps the application and ML inference components decoupled and allows the model to be replaced without rewriting the backend.

---

# Inference Optimization

Because the project was developed under the time constraints of the Synapse Hackathon, training a complete model from scratch was outside the practical development scope.

We therefore started from the pretrained baseline and experimented with improvements around inference.

## Test-Time Augmentation

We used multiple inference views, including the original image and a horizontally flipped version.

```text
             Input Image
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
 Original View        Flipped View
        │                   │
        ▼                   ▼
   Model Inference     Model Inference
        │                   │
        └─────────┬─────────┘
                  ▼
        Combined Prediction
```

The purpose is to make the prediction less dependent on a single image orientation.

## Post-Processing

Small isolated connected components can produce undesirable false positives.

We therefore applied mask cleanup to remove very small isolated regions and improve spatial coherence.

---

# Results

On our hackathon evaluation setup, we observed an improvement over the starting pretrained baseline:

| Configuration                | Dice Score |
| ---------------------------- | ---------: |
| Pretrained baseline          |  **~0.22** |
| Optimized inference pipeline |  **~0.25** |
| Absolute improvement         |  **+0.03** |
| Relative improvement         | **~13.6%** |

### Interpretation

The reported `0.22 → 0.25` improvement represents **our hackathon evaluation setup**.

It should not be interpreted as:

* a new state-of-the-art result
* a clinical validation result
* a direct comparison with every published study
* the official benchmark score of the CPAISD dataset

The objective of the hackathon optimization was to demonstrate that an existing pretrained model could be made more useful through inference-time improvements and integrated into an end-to-end system.

---

# Application Architecture

Policia follows a service-oriented structure:

```text
                   ┌──────────────────┐
                   │     Frontend     │
                   │     Next.js      │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │     FastAPI      │
                   │     Backend      │
                   └───────┬──────────┘
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
          Database      DICOM       Model Service
             │         Processing         │
             │             │              │
             └─────────────┴──────┬───────┘
                                   │
                                   ▼
                             NPZ Result
                                   │
                                   ▼
                        Validation + Analysis
```

This separation makes the application easier to extend with a new trained model in the future.

---

# Backend

The backend is implemented using **FastAPI**.

## Main Responsibilities

### Authentication

The backend provides:

* JWT-based authentication
* Doctor accounts
* Pathologist accounts
* Role-based access
* Password hashing using Argon2

### Scan Management

The backend supports operations such as:

* scan upload
* scan listing
* scan details
* result retrieval
* original slice retrieval
* core mask retrieval
* penumbra mask retrieval

### Model Communication

The segmentation model is accessed through a configurable service endpoint.

The integration contract is intentionally simple:

```http
POST /predict
Content-Type: multipart/form-data
```

Input:

```text
DICOM ZIP
```

Output:

```text
segmentation.npz
```

---

# DICOM Processing

The upload pipeline is designed around DICOM studies.

The backend:

1. receives the uploaded ZIP archive
2. validates the upload
3. prevents unsafe extraction paths
4. extracts DICOM files
5. validates the DICOM objects
6. identifies the imaging slices
7. orders slices using available spatial metadata
8. stores the scan metadata
9. sends the study to the model service

The design allows the model service to remain independent from the web application.

---

# Segmentation Result Handling

The model service returns a compressed NumPy archive containing a segmentation array.

Expected output:

```python
segmentation
```

Expected dimensions:

```text
[height, width, number_of_slices]
```

Expected labels:

```text
0 = Background
1 = Penumbra
2 = Core
```

The backend validates the returned array before downstream processing.

Validation includes:

* dimensionality
* slice-count consistency
* integer labels
* allowed class values

This prevents malformed or incompatible model responses from silently entering the analysis pipeline.

---

# Quantitative Analysis

The current backend performs prototype quantitative calculations based on segmentation labels.

## Core

Pixels with label `2` are treated as ischemic core.

## Penumbra

Pixels with label `1` are treated as penumbra.

## Mismatch Volume

```text
Mismatch Volume = Penumbra Volume − Core Volume
```

## Mismatch Ratio

```text
Mismatch Ratio = Penumbra Volume / Core Volume
```

When core volume is zero, the ratio is undefined rather than dividing by zero.

## Current Prototype Calculation

The current implementation uses a simplified approximation based on label counts and a configured average brain height.

This is intentionally a **prototype calculation** and should not be interpreted as an accurate clinical physical volume in milliliters.

A future implementation will use the actual DICOM voxel dimensions and slice geometry.

---

# Authentication and Access Control

The application includes a role-based workflow.

### Pathologist

Responsible for:

* uploading imaging studies
* initiating the processing workflow
* reviewing model outputs

### Doctor

Can access assigned scan results and review the AI-generated analysis.

The backend uses JWT authentication and Argon2 password hashing.

---

# Frontend

The frontend is built with:

* **Next.js 14**
* **React 18**
* **TypeScript**
* **Tailwind CSS**
* **Lucide React**

The interface was designed as a clinician-oriented imaging dashboard for the hackathon demonstration.

## Current UI Capabilities

The frontend includes:

* imaging upload workflow
* sample-case workflow
* image visualization
* slice navigation
* segmentation overlay controls
* processing-state visualization
* core/penumbra result panels
* report drafting workflow
* report copy/download functionality
* clinician-oriented review layout

---

# Important Prototype Distinction

The current repository contains both **real backend integration code** and a **frontend demonstration layer**.

The backend is structured for real model integration and can communicate with a separate inference service.

However, parts of the current frontend are intentionally demonstrational because the complete live clinical inference workflow was not fully integrated during the hackathon.

For example, some UI values and processing states are illustrative rather than generated live from the segmentation model.

This was a deliberate trade-off to deliver a complete hackathon demonstration within the available development time.

---

# Mock Model Service

The repository also contains a deterministic mock model service.

Its purpose is to allow the backend to be tested without requiring the actual medical segmentation model.

```text
Backend
   │
   ▼
MODEL_API_URL
   │
   ▼
Mock Model
   │
   ▼
segmentation.npz
```

The mock service produces the expected NPZ structure but **does not perform genuine medical-image segmentation**.

It should therefore only be used for development and API testing.

---

# Project Structure

```text
Policia-1/
│
├── Backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── deps.py
│   │   │   └── scans.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   │
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   └── scan.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── account.py
│   │   │   └── auth.py
│   │   │
│   │   ├── services/
│   │   │   ├── model_client.py
│   │   │   ├── scan_service.py
│   │   │   └── volume_service.py
│   │   │
│   │   ├── utils/
│   │   │   └── file_utils.py
│   │   │
│   │   └── main.py
│   │
│   ├── mock_model/
│   │   └── main.py
│   │
│   ├── requirements.txt
│   ├── alembic.ini
│   └── README.md
│
└── Frontend/
    ├── app/
    │   ├── page.tsx
    │   ├── layout.tsx
    │   └── globals.css
    │
    ├── public/
    ├── package.json
    ├── postcss.config.mjs
    └── tailwind.config.ts
```

---

# Technology Stack

| Component            | Technology                    |
| -------------------- | ----------------------------- |
| Frontend             | Next.js 14                    |
| Frontend Language    | TypeScript                    |
| UI                   | React + Tailwind CSS          |
| Icons                | Lucide React                  |
| Backend              | FastAPI                       |
| ORM                  | SQLAlchemy                    |
| Database             | Configurable SQL database     |
| Authentication       | JWT                           |
| Password Hashing     | Argon2                        |
| Medical Imaging      | pydicom                       |
| Numerical Processing | NumPy                         |
| Image Utilities      | Pillow                        |
| HTTP Client          | HTTPX                         |
| Database Migration   | Alembic                       |
| ML Integration       | External segmentation service |
| Testing              | Pytest                        |

---

# Installation

## Clone the Repository

```bash
git clone https://github.com/GargiPareek-27/Policia-1.git
cd Policia-1
```

---

# Running the Backend

Move into the backend:

```bash
cd Backend
```

## Create a Virtual Environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Environment Configuration

Create the environment file:

### Windows

```powershell
Copy-Item .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Configure the required values, for example:

```env
DATABASE_URL=sqlite:///./strokecore.db
JWT_SECRET=your-secret-key
MODEL_API_URL=http://127.0.0.1:8001
MODEL_API_KEY=
UPLOAD_DIR=./uploads
MAX_UPLOAD_MB=512
AVERAGE_BRAIN_HEIGHT_MM=150
```

Use secure values for any deployment environment.

## Run Database Migrations

```bash
python -m alembic upgrade head
```

## Start the Mock Model

From the `Backend` directory:

```bash
python -m uvicorn mock_model.main:app --host 127.0.0.1 --port 8001
```

## Start the Backend

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

---

# Running the Frontend

Open a second terminal and move into:

```bash
cd Frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

---

# Example End-to-End Backend Flow

```text
Pathologist Login
       │
       ▼
Upload DICOM ZIP
       │
       ▼
Archive Validation
       │
       ▼
DICOM Extraction
       │
       ▼
Slice Ordering
       │
       ▼
Model Service Request
       │
       ▼
Segmentation NPZ
       │
       ▼
NPZ Validation
       │
       ├───────────────┐
       ▼               ▼
   Core Mask      Penumbra Mask
       │               │
       └───────┬───────┘
               ▼
      Quantitative Analysis
               │
               ▼
       Database / Storage
               │
               ▼
        Authorized Review
```

---

# Current Status

## Implemented

* Pretrained stroke-segmentation model integration contract
* DICOM ZIP ingestion
* Archive safety checks
* DICOM validation
* Slice ordering
* FastAPI backend
* Model-service abstraction
* NPZ segmentation validation
* Core/penumbra mask handling
* Prototype quantitative analysis
* Mismatch calculation
* Scan metadata persistence
* JWT authentication
* Argon2 password hashing
* Role-based access
* Mock model service
* Next.js frontend
* Slice navigation UI
* Segmentation overlay UI
* Review-oriented dashboard
* Report drafting interface

---

# Limitations

Policia is currently a **hackathon/research prototype**, and several limitations remain.

## 1. Pretrained Model

The current segmentation model originated from an existing research baseline rather than a model trained from scratch by the team during the hackathon.

## 2. Limited Training Time

The Synapse Hackathon imposed a limited development timeline. Training and extensively validating a dedicated model on CPAISD was therefore outside the immediate hackathon scope.

## 3. Prototype Evaluation

The `~0.22 → ~0.25` Dice improvement reflects our own hackathon evaluation setup.

A larger, patient-level evaluation is required to establish whether the improvement is robust.

## 4. Clinical Validation

The system has not been clinically validated.

It should not be used as an autonomous diagnostic tool.

## 5. Prototype Volume Estimation

The current volume calculation is simplified and is not equivalent to a clinically calibrated physical volume measurement.

## 6. Frontend Demonstration Components

Some frontend metrics, confidence/reliability values, processing states, and sample case outputs are illustrative.

They should not be interpreted as validated real-time clinical predictions.

## 7. MRI Support

The application architecture allows imaging metadata associated with multiple modalities, but the pretrained stroke pipeline used in this project is based on the relevant NCCT research setting. General MRI inference is therefore not established by the current model.

## 8. RAG / Reporting

The project concept includes grounded medical reporting and precaution generation, but a production-grade medical RAG pipeline is not fully implemented in the current repository.

---

# Future Improvements

The hackathon implementation is intended to serve as the foundation for a more rigorous research version of the project.

## 1. Train a Dedicated Model on CPAISD

The most important next step is to train and fine-tune our **own segmentation model on the CPAISD dataset**.

Instead of depending exclusively on an existing pretrained checkpoint, we plan to establish a reproducible training pipeline including:

* dataset preprocessing
* patient-level train/validation/test splits
* class balancing
* augmentation
* model training
* checkpoint selection
* systematic evaluation

Candidate architectures include:

* FPN-based models
* U-Net / UNet++
* Transformer-based segmentation
* CNN-Transformer hybrid architectures

---

## 2. Improve Core Segmentation

The ischemic core is particularly challenging to detect accurately.

Future work will investigate:

* Dice + Cross-Entropy losses
* Focal / Tversky loss
* class-imbalance handling
* multi-scale features
* hard-example mining
* improved augmentation
* 2.5D contextual modeling
* full 3D architectures

The goal is to improve both **core and penumbra segmentation**, rather than optimizing only overall Dice.

---

## 3. Reproduce Stronger Research Approaches

Our literature review found research approaches reporting stronger segmentation performance, but direct reproduction is not always straightforward.

Some studies use:

* different datasets
* different imaging modalities
* different preprocessing pipelines
* different train/test splits
* private or unavailable training data
* unavailable pretrained checkpoints

Therefore, rather than directly comparing isolated Dice values from different papers, we plan to build a **controlled CPAISD benchmark** where candidate architectures are trained and evaluated under the same conditions.

This will provide a more meaningful and reproducible comparison.

---

## 4. Comprehensive Evaluation

Future experiments will report multiple metrics instead of relying on one headline Dice value.

```text
Core Dice
Penumbra Dice
Precision
Recall / Sensitivity
Specificity
HD95
Volume Error
Mismatch-Ratio Error
```

Evaluation will be performed at the patient/study level with strict separation between training, validation, and test data.

---

## 5. Accurate Physical Volume Computation

The current approximation will be replaced by a calculation using actual DICOM voxel geometry.

Conceptually:

```text
Voxel Volume
    =
Pixel Spacing X
×
Pixel Spacing Y
×
Slice Thickness / Spacing

Lesion Volume
    =
Number of Lesion Voxels
×
Voxel Volume
```

This will allow the system to derive physically meaningful lesion volumes.

---

## 6. Full 3D Visualization

Future versions can include:

* axial/sagittal/coronal views
* synchronized navigation
* 3D lesion rendering
* editable segmentation masks
* overlay comparison
* quantitative region-of-interest analysis

---

## 7. End-to-End Model Integration

The trained model will eventually be integrated directly into the inference service:

```text
DICOM
  ↓
Preprocessing
  ↓
Dedicated CPAISD Model
  ↓
TTA / Ensemble
  ↓
Post-Processing
  ↓
Core + Penumbra Masks
  ↓
3D Quantitative Analysis
  ↓
Visualization
```

---

## 8. Independent Validation

Before any consideration of clinical deployment, the model should be evaluated on independent datasets and across variations in:

* scanners
* acquisition protocols
* hospitals
* patient populations
* image quality

This is necessary to understand generalization beyond the training dataset.

---

## 9. Grounded Medical Reporting

The reporting layer can be extended using a retrieval-augmented approach grounded in validated medical references.

The intended workflow is:

```text
Segmentation + Quantitative Results
                ↓
        Structured Findings
                ↓
      Medical Knowledge Retrieval
                ↓
       Draft Explanation/Report
                ↓
          Clinician Review
```

The system should remain **clinician-in-the-loop** and should not autonomously make treatment recommendations.

---

# Research Direction

The project has two distinct stages.

### Hackathon Stage

```text
Publicly Available Pretrained Model
                 ↓
       Inference Optimization
                 ↓
        ~0.22 → ~0.25 Dice
                 ↓
      Full-Stack Prototype
```

### Research Stage

```text
             CPAISD Dataset
                    ↓
        Dedicated Model Training
                    ↓
       Architecture Experiments
                    ↓
      Controlled Benchmarking
                    ↓
        Advanced Segmentation
                    ↓
       Rigorous Evaluation
                    ↓
       Independent Validation
```

The hackathon implementation therefore serves as a **foundation for subsequent model-development and research work**, rather than the final model.

---

# Why We Started with a Pretrained Model

Training a high-quality medical-image segmentation model from scratch requires substantial experimentation in:

* preprocessing
* augmentation
* architecture selection
* hyperparameter tuning
* class-imbalance handling
* validation
* compute resources

Given the limited duration of the Synapse Hackathon, the practical approach was to start with a publicly available pretrained research baseline and concentrate on delivering an end-to-end working system.

This allowed us to demonstrate:

```text
Existing Research Model
        +
Inference Optimization
        +
Medical Imaging Pipeline
        +
Backend Engineering
        +
Visualization
        =
End-to-End Hackathon Prototype
```

The research phase will then focus on training and evaluating models directly on CPAISD.

---

# A Note on Research Comparisons

Published Dice scores should be interpreted carefully.

A higher Dice reported by another paper does not automatically imply that its approach would achieve the same result on our setup because reported results can depend on:

* dataset composition
* data splits
* modality
* preprocessing
* annotation protocol
* evaluation metric
* patient population
* training procedure
* availability of pretrained weights

For this reason, future comparisons will prioritize **reproducibility and controlled evaluation** over simply comparing numbers reported across unrelated experiments.

---

# Acknowledgements

This project builds upon publicly available research in hyperacute ischemic stroke segmentation, particularly the **CPAISD / Early Hyperacute Stroke** work and its released baseline implementation.

We acknowledge the researchers and institutions who made the underlying dataset, baseline code, and research resources available to the community.

---

# References

1. Umerenkov, D., Kudin, S., Peksheva, M. et al. **Core-Penumbra Hyperacute Ischemic Stroke Dataset.** *Scientific Data*, 2025.

2. **Early Hyperacute Stroke Dataset — Baseline Implementation and Model**
   `sb-ai-lab/early_hyperacute_stroke_dataset`

3. Additional stroke-segmentation literature reviewed during the research phase should be cited alongside any future model comparison or benchmark results.

---

# Repository

**GitHub:**
https://github.com/GargiPareek-27/Policia-1

---

# Disclaimer

**Policia / StrokeGuard AI is a research and hackathon prototype intended for educational and experimental purposes only.**

The system has **not been clinically validated** and must not be used to:

* diagnose patients
* determine treatment eligibility
* recommend treatment
* replace a qualified medical professional
* make autonomous clinical decisions

All AI-generated outputs should be independently reviewed by appropriately qualified medical professionals.
