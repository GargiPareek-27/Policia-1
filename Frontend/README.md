# StrokeGuard AI — Clinical Dashboard (Fixed)

This is the **upload-first premium white healthcare dashboard** for the hackathon demo.

## Run in VS Code

Open **this exact folder** — the folder containing `package.json`.

```bash
npm install
npm run dev
```

Then open:

http://localhost:3000

## What is implemented

- Upload-first clinical dashboard.
- CT/MRI/DICOM/NIfTI file selection UI.
- Browser preview for image files.
- Illustrative high-detail brain MRI sample.
- Original vs AI segmentation views.
- Slice navigation + synchronized overlay.
- Overlay opacity control.
- AI reliability / uncertainty panel.
- Research pipeline status showing TTA + post-processing.
- Prototype 3D Dice disclosure (0.22).
- Structured report editor.
- Copy / download report draft.
- Clinician approval state in the demo.
- Patient-facing precaution draft marked as requiring clinician review.

## Not yet a clinical implementation

DICOM/NIfTI parsing, true Cornerstone3D rendering, real model inference, TTA, validated uncertainty estimation, segmentation editing at voxel level, RAG retrieval, PDF generation, authentication, audit logging, and secure clinical infrastructure still need backend/medical-imaging integration.

The sample scan and all displayed measurements/masks are illustrative demo data only.

## Compile fix
The Dashboard icon is imported as `House` so it does not conflict with the page component name `Home`.
