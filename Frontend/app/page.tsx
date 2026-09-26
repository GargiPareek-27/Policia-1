 "use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, Bell, BookOpen, Check, CheckCircle2, ChevronDown, ChevronLeft,
  ChevronRight, CircleHelp, ClipboardList, Download, FileCheck2, FileText,
  House, Info, Layers3, Menu, MoreHorizontal, PanelLeft, Pencil, Play,
  RefreshCw, Search, Settings, ShieldCheck, SlidersHorizontal, Stethoscope,
  UploadCloud, UserRound, X, ZoomIn, Move, Sun, Ruler, RotateCcw, AlertTriangle,
  Sparkles, ExternalLink, Clock3, Database, ScanLine
} from "lucide-react";

type Stage = "idle" | "processing" | "complete";
type FileInfo = { name: string; type: string; size: number };

const slices = Array.from({ length: 11 }, (_, i) => 37 + i);

function BrainImage({
  src,
  overlay,
  opacity,
  slice,
}: {
  src: string;
  overlay: boolean;
  opacity: number;
  slice: number;
}) {
  return (
    <div className="brain-wrap">
      <img src={src} className="brain-img" alt="Illustrative axial brain scan" />
      {overlay && (
        <svg className="mask-layer" viewBox="0 0 100 100" preserveAspectRatio="none">
          <path
            d="M61 30 C69 24,78 27,80 37 C83 46,78 53,79 60 C80 69,73 78,67 74 C61 70,62 63,58 57 C53 49,55 36,61 30Z"
            fill="#ef4d5a"
            fillOpacity={Math.max(0, opacity / 100)}
          />
          <path
            d="M69 25 C78 19,87 24,88 34 C92 44,89 54,85 61 C82 69,88 75,81 82 C76 87,68 82,68 75 C67 68,63 64,65 56 C67 49,61 43,66 36 C67 31,65 28,69 25Z"
            fill="#eab34c"
            fillOpacity={Math.max(0, (opacity / 100) * 0.82)}
          />
          <path
            d="M61 30 C69 24,78 27,80 37 C83 46,78 53,79 60 C80 69,73 78,67 74 C61 70,62 63,58 57 C53 49,55 36,61 30Z"
            fill="none"
            stroke="#ff7a83"
            strokeWidth=".8"
          />
          <path
            d="M69 25 C78 19,87 24,88 34 C92 44,89 54,85 61 C82 69,88 75,81 82 C76 87,68 82,68 75 C67 68,63 64,65 56 C67 49,61 43,66 36 C67 31,65 28,69 25Z"
            fill="none"
            stroke="#ffd57b"
            strokeWidth=".8"
          />
        </svg>
      )}
      <div className="orientation">
        <span>A</span><span>R</span><span>L</span><span>P</span>
      </div>
      <div className="ww">WW 80 · WL 40</div>
      <div className="scale">5 cm</div>
      <div className="slice-hud">S{String(slice).padStart(2, "0")}</div>
    </div>
  );
}

function ToolRail() {
  const tools = [
    [Move, "Pan"], [ZoomIn, "Zoom"], [Sun, "Window"], [Ruler, "Measure"], [RotateCcw, "Reset"]
  ] as const;
  return (
    <div className="viewer-tools">
      {tools.map(([Icon, label], i) => (
        <button key={label} className={"viewer-tool " + (i === 0 ? "selected" : "")} title={label}>
          <Icon size={16}/><span>{label}</span>
        </button>
      ))}
    </div>
  );
}

export default function Home() {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileInfo | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [stage, setStage] = useState<Stage>("idle");
  const [progress, setProgress] = useState(0);
  const [slice, setSlice] = useState(42);
  const [overlay, setOverlay] = useState(true);
  const [opacity, setOpacity] = useState(64);
  const [reportOpen, setReportOpen] = useState(false);
  const [reportApproved, setReportApproved] = useState(false);
  const [showPipeline, setShowPipeline] = useState(false);
  const [toast, setToast] = useState("");
  const [reportText, setReportText] = useState(
`STROKEGUARD AI — STRUCTURED REVIEW DRAFT

Study ID: STK-2024-11-08-7F3A
Modality: CT Perfusion (illustrative demo)
Acquisition: Nov 08, 2024 · 14:32

AI-GENERATED MEASUREMENTS
• Ischemic core volume: 18.4 mL
• Penumbra volume: 38.7 mL
• Mismatch ratio: 2.10
• Total lesion volume: 57.1 mL

MODEL / PIPELINE
• Pretrained segmentation model
• TTA: original + flipped inference (demo)
• Post-processing: small-component cleanup (demo)
• Validation reference: prototype 3D Dice 0.22

CLINICAL REVIEW
AI-assisted measurements are provided for clinician review. Imaging metrics alone do not establish treatment eligibility.

PATIENT-FACING PRECAUTION DRAFT
[AI/RAG DRAFT — REQUIRES CLINICIAN REVIEW]
This section should be finalized only after reviewing the patient record, imaging, contraindications, and local clinical protocol.

CLINICIAN INTERPRETATION
[Enter clinician-approved interpretation]

REVIEW STATUS
Draft — not signed and not finalized.`
  );
  const notify = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  };

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const loadFile = (file?: File) => {
    if (!file) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile({ name: file.name, type: file.type || "application/octet-stream", size: file.size });
    const isPreviewable = file.type.startsWith("image/");
    setPreviewUrl(isPreviewable ? URL.createObjectURL(file) : "");
    setStage("idle");
    setProgress(0);
    notify(isPreviewable ? "Image selected for this demo" : "Study file selected — DICOM/NIfTI viewer requires backend parsing");
  };

  const runAnalysis = () => {
    setStage("processing");
    setProgress(8);
    setShowPipeline(true);
    let value = 8;
    const id = window.setInterval(() => {
      value += 16;
      setProgress(Math.min(value, 100));
      if (value >= 100) {
        window.clearInterval(id);
        setStage("complete");
        notify("Analysis pipeline completed in demo mode");
      }
    }, 360);
  };

  const ratio = useMemo(() => 38.7 / 18.4, []);

  return (
    <main className="app">
      <header className="top">
        <div className="brand">
          <div className="logo"><Activity size={22}/></div>
          <div><div className="brand-name">StrokeGuard <span>AI</span></div><div className="brand-sub">AI-assisted stroke imaging analysis</div></div>
        </div>

        <div className="search"><Search size={16}/><input placeholder="Search patients, studies..." /><span>⌘ K</span></div>

        <div className="top-actions">
          <button className="round-btn"><Bell size={17}/><i/></button>
          <div className="doctor"><div className="avatar">DR</div><div><b>Radiologist</b><small>Clinical workspace</small></div><ChevronDown size={14}/></div>
        </div>
      </header>

      <div className="app-body">
        <aside className="sidebar">
          <nav>
            {[
              [House, "Dashboard"], [UserRound, "Patients"], [ScanLine, "New analysis"],
              [Database, "Studies"], [FileText, "Reports"], [BookOpen, "Knowledge base"], [Settings, "Settings"]
            ].map(([Icon, label], i) => (
              <button key={label} className={"nav-item " + (i === 0 ? "active" : "")}><Icon size={17}/><span>{label}</span></button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <button className="nav-item"><CircleHelp size={17}/><span>Help & support</span></button>
            <div className="profile"><div className="avatar light">PJ</div><div><b>Dr. Priyanshi</b><small>Radiologist</small></div><ChevronDown size={14}/></div>
          </div>
        </aside>

        <section className="main">
          <div className="page-heading">
            <div>
              <div className="eyebrow">CLINICAL WORKSPACE</div>
              <h1>Stroke imaging dashboard</h1>
              <p>Upload a de-identified CT/MRI study, review the AI analysis, and prepare a clinician-approved report.</p>
            </div>
            <div className="header-status"><span className="status-pill"><span className="status-dot"/> Demo environment</span><button className="more"><MoreHorizontal size={18}/></button></div>
          </div>

          <section className="upload-card">
            <div className="upload-copy">
              <div className="upload-circle"><UploadCloud size={22}/></div>
              <div>
                <div className="eyebrow">STEP 01 · START A NEW REVIEW</div>
                <h2>Upload CT or MRI scan</h2>
                <p>Drop a study here or select DICOM, NIfTI, PNG or JPG files. Use de-identified data for the demo.</p>
              </div>
            </div>
            <div className="upload-actions">
              <input ref={fileRef} hidden type="file" accept=".dcm,.nii,.nii.gz,.zip,image/png,image/jpeg,image/webp" multiple onChange={e=>loadFile(e.target.files?.[0])}/>
              <button className="btn primary" onClick={()=>fileRef.current?.click()}><UploadCloud size={16}/> Browse files</button>
              <button className="btn" onClick={()=>{setSelectedFile({name:"Illustrative MRI sample",type:"image/png",size:0});setPreviewUrl("");setStage("complete");setProgress(100);notify("Illustrative sample case loaded")}}><Layers3 size={16}/> Use sample case</button>
            </div>
            <div className="upload-foot"><span><ShieldCheck size={13}/> Patient identifiers should be removed before upload</span><span>Supported: DICOM · NIfTI · PNG · JPG</span></div>
          </section>

          {selectedFile && (
            <section className="selected-study">
              <div className="study-head">
                <div className="study-title"><div className="file-icon"><FileCheck2 size={17}/></div><div><b>{selectedFile.name}</b><small>{selectedFile.size ? `${(selectedFile.size/1024/1024).toFixed(2)} MB` : "Illustrative sample"} · {selectedFile.type || "Study file"}</small></div></div>
                <div className="study-actions">
                  <button className="btn subtle" onClick={()=>setShowPipeline(!showPipeline)}><Activity size={15}/> Pipeline</button>
                  {stage === "complete" ? <span className="complete"><CheckCircle2 size={15}/> Analysis complete</span> : <button className="btn primary" onClick={runAnalysis}><Play size={15}/> Run analysis</button>}
                </div>
              </div>
              {stage === "processing" && <div className="progress-wrap"><div className="progress-meta"><span>AI processing · {progress}%</span><span>Preprocess → TTA → segmentation → cleanup → metrics</span></div><div className="progress"><i style={{width:`${progress}%`}}/></div></div>}
              {showPipeline && (
                <div className="pipeline">
                  {[
                    ["01","Preprocess","CT/MRI normalization"],["02","TTA","Original + flipped inference"],
                    ["03","Segment","Core + penumbra masks"],["04","Post-process","Remove tiny components"],
                    ["05","Metrics","Volume + mismatch"]
                  ].map(([n,title,sub],i)=><div className="pipe-step" key={n}><span className="pipe-num">{n}</span><div><b>{title}</b><small>{sub}</small></div>{stage==="complete" ? <CheckCircle2 className="pipe-ok" size={15}/> : i===0 ? <Clock3 size={14}/> : null}</div>)}
                </div>
              )}
            </section>
          )}

          <section className="dashboard-grid">
            <div className="left-col">
              <div className="section-line"><div><div className="eyebrow">STEP 02 · REVIEW</div><h2>Imaging analysis</h2></div><div className="view-tabs"><button className="tab active"><Layers3 size={14}/> Imaging</button><button className="tab"><ClipboardList size={14}/> Report</button></div></div>

              <div className="imaging-grid">
                <div className="image-card">
                  <div className="image-card-head"><div><b>Original scan</b><small>Axial · grayscale</small></div><span className="series-badge">01 / 120</span></div>
                  <div className="viewer"><ToolRail/><BrainImage src={previewUrl || "/brain-mri-demo.png"} overlay={false} opacity={opacity} slice={slice}/></div>
                  <div className="viewer-controls">
                    <button className="square" onClick={()=>setSlice(v=>Math.max(1,v-1))}><ChevronLeft size={15}/></button>
                    <span>Slice <b>{slice}</b> <em>/ 120</em></span>
                    <input type="range" min="1" max="120" value={slice} onChange={e=>setSlice(+e.target.value)}/>
                    <button className="square" onClick={()=>setSlice(v=>Math.min(120,v+1))}><ChevronRight size={15}/></button>
                  </div>
                </div>

                <div className="image-card">
                  <div className="image-card-head"><div><b>AI segmentation</b><small>Core + penumbra</small></div><button className={"switch " + (overlay ? "on" : "")} onClick={()=>setOverlay(!overlay)}><span/></button></div>
                  <div className="viewer"><ToolRail/><BrainImage src={previewUrl || "/brain-mri-demo.png"} overlay={overlay} opacity={opacity} slice={slice}/><div className="legend-dark"><span><i className="core"/> Ischemic core</span><span><i className="pen"/> Penumbra</span></div></div>
                  <div className="viewer-controls">
                    <span>Overlay opacity</span><input type="range" min="0" max="100" value={opacity} onChange={e=>setOpacity(+e.target.value)}/><b>{opacity}%</b>
                    <button className="square" onClick={()=>setSlice(v=>Math.max(1,v-1))}><ChevronLeft size={15}/></button>
                    <button className="square" onClick={()=>setSlice(v=>Math.min(120,v+1))}><ChevronRight size={15}/></button>
                  </div>
                </div>
              </div>

              <div className="filmstrip">
                <div className="film-head"><div><b>Axial series</b><span> · synchronized navigation</span></div><span>Showing {Math.max(1,slice-5)}–{Math.min(120,slice+5)} / 120</span></div>
                <div className="film-row"><button onClick={()=>setSlice(v=>Math.max(1,v-5))}><ChevronLeft size={16}/></button>{slices.map(s=><button key={s} onClick={()=>setSlice(s)} className={"thumb " + (s===slice ? "sel" : "")}><img src="/brain-mri-demo.png" alt="slice thumbnail"/><span>{s}</span></button>)}<button onClick={()=>setSlice(v=>Math.min(120,v+5))}><ChevronRight size={16}/></button></div>
              </div>
            </div>

            <aside className="right-col">
              <div className="result-head"><div><div className="eyebrow">STEP 03 · RESULTS</div><h2>Key measurements</h2></div><button className="icon-plain" onClick={()=>notify("Demo metrics are illustrative")}><RefreshCw size={16}/></button></div>

              <div className="metric-grid">
                <div className="metric red"><span>Ischemic core</span><strong>18.4</strong><small>mL · AI estimate</small></div>
                <div className="metric amber"><span>Penumbra</span><strong>38.7</strong><small>mL · AI estimate</small></div>
                <div className="metric blue"><span>Mismatch ratio</span><strong>{ratio.toFixed(2)}</strong><small>penumbra ÷ core</small></div>
              </div>

              <div className="small-panel">
                <div className="panel-title"><span>Model reliability</span><Info size={14}/></div>
                {[
                  ["Core segmentation","0.82 ± 0.11","82%","#ef6670"],
                  ["Penumbra segmentation","0.71 ± 0.18","71%","#e9b34f"],
                  ["Boundary uncertainty","0.28","28%","#76a9d2"]
                ].map(([label,value,width,color])=><div className="rel-row" key={label}><div className="rel-top"><span>{label}</span><b>{value}</b></div><div className="rel-track"><i style={{width,background:color}}/></div></div>)}
                <div className="micro-note"><AlertTriangle size={13}/> Reliability values are illustrative until generated by the validated model.</div>
              </div>

              <div className="small-panel">
                <div className="panel-title"><span>Research / pipeline status</span><Info size={14}/></div>
                <div className="mini-grid">
                  <div><span>TTA</span><b>Ready</b><small>2-view ensemble</small></div>
                  <div><span>Cleanup</span><b>Ready</b><small>small components</small></div>
                  <div><span>3D Dice</span><b>0.22</b><small>prototype baseline</small></div>
                  <div><span>Report draft</span><b>AI-assisted</b><small>clinician approval</small></div>
                </div>
              </div>

              <div className="clinical-panel">
                <div className="panel-title"><span>Clinical context</span><Info size={14}/></div>
                <div className="clinical-main"><div className="context-icon"><Stethoscope size={17}/></div><div><b>Computed mismatch ratio: 2.10</b><p>No treatment recommendation is generated by this prototype. Clinical interpretation remains with the treating professional.</p></div></div>
              </div>

              <div className="report-preview">
                <div className="report-top"><div><div className="eyebrow">STEP 04 · DOCUMENT</div><h2>Structured report</h2></div><span className="draft">DRAFT</span></div>
                <div className="report-body">
                  <div className="report-line"><span>Study ID</span><b>STK-2024-11-08-7F3A</b></div>
                  <div className="report-line"><span>Core volume</span><b>18.4 mL</b></div>
                  <div className="report-line"><span>Penumbra</span><b>38.7 mL</b></div>
                  <div className="report-line"><span>Mismatch ratio</span><b>2.10</b></div>
                  <div className="report-sep"/>
                  <p className="ai-draft"><Sparkles size={13}/> AI/RAG precaution draft is available for clinician review.</p>
                </div>
                <div className="report-actions"><button className="btn" onClick={()=>setReportOpen(true)}><FileText size={15}/> Open & edit</button><button className="btn primary" onClick={()=>setReportOpen(true)}><Download size={15}/> Generate report</button></div>
              </div>
            </aside>
          </section>

          <footer className="footer-note"><span><ShieldCheck size={13}/> De-identified demo · no live patient data</span><span>AI-assisted measurements · clinician review required</span><button onClick={()=>notify("About this prototype")}>About StrokeGuard AI <ExternalLink size={11}/></button></footer>
        </section>
      </div>

      {reportOpen && (
        <div className="modal-backdrop">
          <div className="report-modal">
            <div className="modal-head"><div><div className="eyebrow">REPORT WORKSPACE</div><h2><FileText size={19}/> Structured report draft</h2></div><button className="icon-plain" onClick={()=>setReportOpen(false)}><X size={18}/></button></div>
            <div className="modal-info"><AlertTriangle size={15}/> Demo document with illustrative measurements. Do not use as a clinical report.</div>
            <textarea value={reportText} onChange={e=>setReportText(e.target.value)} />
            <div className="modal-bottom"><div className={"approval " + (reportApproved ? "approved" : "")}>{reportApproved ? <CheckCircle2 size={15}/> : <Clock3 size={15}/>} {reportApproved ? "Clinician review recorded in demo" : "Awaiting clinician review"}</div><div className="modal-actions"><button className="btn" onClick={()=>navigator.clipboard?.writeText(reportText).then(()=>notify("Report copied"))}><ClipboardList size={15}/> Copy</button><button className="btn" onClick={()=>{const blob=new Blob([reportText],{type:"text/plain"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="strokeguard-report-draft.txt";a.click();URL.revokeObjectURL(a.href);notify("Draft downloaded")}}><Download size={15}/> Download draft</button><button className="btn primary" onClick={()=>{setReportApproved(true);notify("Clinician review marked in demo")}}><Check size={15}/> Approve draft</button></div></div>
          </div>
        </div>
      )}

      {toast && <div className="toast"><CheckCircle2 size={16}/>{toast}</div>}
    </main>
  );
}
