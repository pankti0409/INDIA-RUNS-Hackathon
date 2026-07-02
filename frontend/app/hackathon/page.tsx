"use client";

import React, { useState, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import Link from "next/link";

type CandidateResult = {
  candidate_id: string;
  rank: number;
  score: number;
  name: string;
  title: string;
  reasoning: string;
  score_breakdown: {
    title_score: number;
    skill_score: number;
    experience_score: number;
    behavioral_score: number;
    education_score: number;
    github_score: number;
    honeypot_probability: number;
  };
};

type APIResponse = {
  status: string;
  total_candidates: number;
  validation_errors_count: number;
  malformed_candidates_count: number;
  results: CandidateResult[];
  reports: Record<string, string>;
};

type UploadedFileEntry = {
  id: string;
  name: string;
  size: string;
  type: string;
  status: "Uploading" | "Ready" | "Parsed" | "Validated" | "Error";
  progress: number;
  validationNotes?: string;
  error?: string;
  metadata?: any;
};

export default function HackathonPage() {
  const [filesList, setFilesList] = useState<UploadedFileEntry[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState("");
  const [response, setResponse] = useState<APIResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedReport, setSelectedReport] = useState("schema_validation");
  const [inspectedCandidate, setInspectedCandidate] = useState<CandidateResult | null>(null);
  const [inspectedCandidateData, setInspectedCandidateData] = useState<any>(null);
  const [loadingInspection, setLoadingInspection] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Drag handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = (files: FileList) => {
    Array.from(files).forEach((file) => {
      const fileId = Math.random().toString(36).substring(2, 9);
      const newEntry: UploadedFileEntry = {
        id: fileId,
        name: file.name,
        size: (file.size / 1024).toFixed(1) + " KB",
        type: "Detecting...",
        status: "Uploading",
        progress: 0,
      };
      
      setFilesList((prev) => [...prev, newEntry]);

      const formData = new FormData();
      formData.append("file", file);

      const xhr = new XMLHttpRequest();
      
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const pct = Math.round((event.loaded / event.total) * 100);
          setFilesList((prev) =>
            prev.map((f) => (f.id === fileId ? { ...f, progress: pct } : f))
          );
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const res = JSON.parse(xhr.responseText);
            if (res.status === "success") {
              let validationNotes = "";
              let status: "Ready" | "Parsed" | "Validated" | "Error" = "Ready";

              if (res.type === "Candidate Dataset") {
                const total = res.metadata?.total_records || 0;
                const malformed = res.metadata?.malformed_records_count || 0;
                validationNotes = `✓ ${total.toLocaleString()} candidate records found`;
                if (malformed > 0) {
                  validationNotes += ` (⚠ ${malformed} malformed)`;
                }
                status = "Ready";
              } else if (res.type === "Job Description") {
                validationNotes = `✓ Parsed successfully (Title: ${res.metadata?.job_title || "Unknown"})`;
                status = "Parsed";
              } else if (res.type === "Schema Definition") {
                validationNotes = `✓ Validated (${res.metadata?.properties_count || 0} properties)`;
                status = "Validated";
              } else if (res.type === "Resume Collection") {
                validationNotes = "✓ Resumes parsed";
                status = "Ready";
              } else if (res.type === "Submission File") {
                validationNotes = `✓ Loaded (${res.metadata?.rows_count || 0} ranked candidates)`;
                status = "Ready";
              } else {
                validationNotes = "✓ Unknown structure validated";
                status = "Ready";
              }

              setFilesList((prev) =>
                prev.map((f) =>
                  f.id === fileId
                    ? {
                        ...f,
                        type: res.type,
                        status: status,
                        progress: 100,
                        validationNotes: validationNotes,
                        metadata: res.metadata,
                      }
                    : f
                )
              );
            } else {
              setFilesList((prev) =>
                prev.map((f) =>
                  f.id === fileId
                    ? {
                        ...f,
                        status: "Error",
                        progress: 0,
                        error: res.error || "File validation failed",
                        validationNotes: res.error || "File validation failed",
                      }
                    : f
                )
              );
            }
          } catch (err) {
            setFilesList((prev) =>
              prev.map((f) =>
                f.id === fileId
                  ? {
                      ...f,
                      status: "Error",
                      progress: 0,
                      error: "Failed to parse validation response",
                      validationNotes: "Failed to parse validation response",
                    }
                  : f
              )
            );
          }
        } else {
          try {
            const errRes = JSON.parse(xhr.responseText);
            setFilesList((prev) =>
              prev.map((f) =>
                f.id === fileId
                  ? {
                      ...f,
                      status: "Error",
                      progress: 0,
                      error: errRes.detail || "Server validation error",
                      validationNotes: errRes.detail || "Server validation error",
                    }
                  : f
              )
            );
          } catch (e) {
            setFilesList((prev) =>
              prev.map((f) =>
                f.id === fileId
                  ? {
                      ...f,
                      status: "Error",
                      progress: 0,
                      error: `HTTP Error ${xhr.status}`,
                      validationNotes: `HTTP Error ${xhr.status}`,
                    }
                  : f
              )
            );
          }
        }
      };

      xhr.onerror = () => {
        setFilesList((prev) =>
          prev.map((f) =>
            f.id === fileId
              ? {
                  ...f,
                  status: "Error",
                  progress: 0,
                  error: "Network error during validation",
                  validationNotes: "Network error during validation",
                }
              : f
          )
        );
      };

      xhr.open("POST", "http://127.0.0.1:8124/api/hackathon/validate-file");
      xhr.send(formData);
    });
  };

  const removeFile = (id: string) => {
    setFilesList((prev) => prev.filter((f) => f.id !== id));
  };

  const clearAllFiles = () => {
    setFilesList([]);
  };

  async function handleRank() {
    setLoading(true);
    setErrorMessage("");
    setResponse(null);
    setInspectedCandidate(null);
    setInspectedCandidateData(null);

    const stages = [
      "Verifying uploaded candidates and parameters...",
      "Loading candidate dataset and schemas...",
      "Extracting Job Description semantic requirements...",
      "Evaluating dense BGE embeddings context...",
      "Computing Cross-Encoder re-ranking weights...",
      "Calculating behavioral signals & open-to-work flags...",
      "Running Honeypot security checks & profile verifications...",
      "Generating final reports & exporting submission.csv..."
    ];

    let stageIdx = 0;
    setLoadingStage(stages[0]);
    const timer = setInterval(() => {
      if (stageIdx < stages.length - 1) {
        stageIdx++;
        setLoadingStage(stages[stageIdx]);
      }
    }, 2500);

    try {
      const useUploaded = filesList.some((f) => f.type === "Candidate Dataset" && f.status === "Ready");
      const res = await fetch(`http://127.0.0.1:8124/api/hackathon/rank?use_uploaded=${useUploaded}`, {
        method: "POST",
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "One-click ranking pipeline failed.");
      }
      setResponse(data);
    } catch (e: any) {
      setErrorMessage(e.message);
    } finally {
      clearInterval(timer);
      setLoading(false);
      setLoadingStage("");
    }
  }

  async function inspectCandidate(cand: CandidateResult) {
    setInspectedCandidate(cand);
    setLoadingInspection(true);
    setInspectedCandidateData(null);
    try {
      const res = await fetch(`http://127.0.0.1:8124/api/candidate/${cand.candidate_id}`);
      if (res.ok) {
        const data = await res.json();
        setInspectedCandidateData(data);
      } else {
        setInspectedCandidateData({
          candidate_id: cand.candidate_id,
          profile: {
            anonymized_name: cand.name,
            current_title: cand.title,
            years_of_experience: 5.0,
            location: "India"
          },
          skills: []
        });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingInspection(false);
    }
  }

  // Previews derived states
  const datasetFile = filesList.find((f) => f.type === "Candidate Dataset" && f.status === "Ready");
  const datasetMetadata = datasetFile?.metadata;

  const jdFileEntry = filesList.find((f) => f.type === "Job Description" && f.status === "Parsed");
  const jdMetadata = jdFileEntry?.metadata;

  const schemaFileEntry = filesList.find((f) => f.type === "Schema Definition" && f.status === "Validated");
  const schemaMetadata = schemaFileEntry?.metadata;

  // Filter dataset sample rows
  const filteredSamples = (datasetMetadata?.sample_records || []).filter((cand: any) => {
    const q = searchQuery.toLowerCase();
    const cid = (cand.candidate_id || "").toLowerCase();
    const name = (cand.profile?.anonymized_name || "").toLowerCase();
    const title = (cand.profile?.current_title || "").toLowerCase();
    return cid.includes(q) || name.includes(q) || title.includes(q);
  });

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto", position: "relative" }}>
        
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-0.03em", color: "var(--text-primary)" }}>
            ⚡ Ingestion &amp; Discovery Hub
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Upload datasets, parse job requirements, customize validation schema, and run ranking cascades in a unified platform.
          </p>
        </div>

        {/* Drag and Drop Zone */}
        <div
          style={{
            border: dragActive ? "2px dashed var(--accent-dark)" : "1px solid var(--border)",
            background: dragActive ? "rgba(168, 197, 218, 0.08)" : "var(--card)",
            borderRadius: "var(--radius)",
            padding: "40px 24px",
            textAlign: "center",
            cursor: "pointer",
            transition: "all 0.2s ease-in-out",
            marginBottom: 24,
          }}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <div style={{ fontSize: 40, marginBottom: 12 }}>📥</div>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
            Drag &amp; drop files or folders here to validate
          </h3>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 14 }}>
            Or click to browse from your device
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center", maxWidth: 600, margin: "0 auto" }}>
            {[".jsonl.gz", ".jsonl", ".json", ".csv", ".xlsx", ".zip", ".md", ".pdf", ".txt"].map((ext) => (
              <span key={ext} style={{ fontSize: 10, background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text-secondary)", padding: "2px 8px", borderRadius: 4, fontWeight: 500 }}>
                {ext}
              </span>
            ))}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: "none" }}
            onChange={handleFileInputChange}
          />
        </div>

        {/* Upload Dashboard Table */}
        {filesList.length > 0 && (
          <div className="card" style={{ marginBottom: 24, padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>Upload Validation Dashboard</h3>
              <button
                onClick={clearAllFiles}
                style={{ background: "none", border: "1px solid var(--border)", color: "var(--text-secondary)", fontSize: 11, padding: "4px 10px", borderRadius: 4, cursor: "pointer", fontWeight: 500 }}
              >
                Clear All
              </button>
            </div>
            
            <div style={{ overflowX: "auto" }}>
              <table className="data-table" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th>File Name</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Status</th>
                    <th>Validation Summary</th>
                    <th style={{ width: 60, textAlign: "right" }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filesList.map((file) => {
                    let typeBadgeColor = "var(--bg)";
                    let typeTextColor = "var(--text-secondary)";
                    if (file.type === "Candidate Dataset") {
                      typeBadgeColor = "rgba(168, 197, 218, 0.15)";
                      typeTextColor = "var(--accent-dark)";
                    } else if (file.type === "Job Description") {
                      typeBadgeColor = "rgba(183, 217, 178, 0.15)";
                      typeTextColor = "#2e7d32";
                    } else if (file.type === "Schema Definition") {
                      typeBadgeColor = "rgba(242, 214, 162, 0.15)";
                      typeTextColor = "#b7791f";
                    } else if (file.type === "Resume Collection") {
                      typeBadgeColor = "rgba(143, 174, 198, 0.15)";
                      typeTextColor = "#1565c0";
                    } else if (file.type === "Submission File") {
                      typeBadgeColor = "rgba(183, 217, 178, 0.15)";
                      typeTextColor = "#2e7d32";
                    }

                    let statusBadgeColor = "var(--bg)";
                    let statusTextColor = "var(--text-secondary)";
                    if (file.status === "Uploading") {
                      statusBadgeColor = "#fef3c7";
                      statusTextColor = "#d97706";
                    } else if (file.status === "Ready" || file.status === "Validated" || file.status === "Parsed") {
                      statusBadgeColor = "#d1fae5";
                      statusTextColor = "#065f46";
                    } else if (file.status === "Error") {
                      statusBadgeColor = "#fee2e2";
                      statusTextColor = "#991b1b";
                    }

                    return (
                      <tr key={file.id}>
                        <td style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{file.name}</td>
                        <td>
                          <span style={{ fontSize: 10, background: typeBadgeColor, color: typeTextColor, padding: "2px 6px", borderRadius: 4, fontWeight: 600 }}>
                            {file.type}
                          </span>
                        </td>
                        <td style={{ fontSize: 11, color: "var(--text-secondary)" }}>{file.size}</td>
                        <td>
                          <span style={{ fontSize: 10, background: statusBadgeColor, color: statusTextColor, padding: "2px 6px", borderRadius: 4, fontWeight: 600 }}>
                            {file.status}
                          </span>
                        </td>
                        <td style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                          {file.status === "Uploading" ? (
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <div style={{ flex: 1, height: 4, background: "var(--border)", borderRadius: 2, minWidth: 100 }}>
                                <div style={{ height: "100%", width: `${file.progress}%`, background: "var(--accent-dark)", borderRadius: 2 }} />
                              </div>
                              <span>{file.progress}%</span>
                            </div>
                          ) : (
                            file.validationNotes
                          )}
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <button
                            onClick={() => removeFile(file.id)}
                            style={{ background: "none", border: "none", color: "#dc2626", fontSize: 11, cursor: "pointer", padding: "4px 8px" }}
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Dynamic File Previews Panels */}
        {(datasetMetadata || jdMetadata || schemaMetadata) && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24, marginBottom: 24 }}>
            
            {/* Candidate Dataset JSONL Preview */}
            {datasetMetadata && (
              <div className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: 12, marginBottom: 16 }}>
                  <div>
                    <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
                      📋 JSONL Candidate Dataset Inspector
                    </h3>
                    <p style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
                      Inspect structured schema profile, missing metrics, and search sample candidate records.
                    </p>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 600, background: "var(--bg)", border: "1px solid var(--border)", padding: "4px 10px", borderRadius: 6 }}>
                    {datasetMetadata.total_records?.toLocaleString() || 0} total records
                  </span>
                </div>

                {/* Distributions grid */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 20 }}>
                  {Object.entries(datasetMetadata.field_distribution || {}).map(([field, pct]: [string, any]) => {
                    const missingCount = datasetMetadata.missing_field_analysis?.[field] || 0;
                    return (
                      <div key={field} style={{ background: "var(--bg)", padding: "10px 12px", borderRadius: 6, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 4 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, fontWeight: 600 }}>
                          <span style={{ color: "var(--text-primary)" }}>{field}</span>
                          <span style={{ color: "var(--text-secondary)" }}>{(pct * 100).toFixed(0)}%</span>
                        </div>
                        <div className="progress-bar" style={{ height: 4 }}>
                          <div className="progress-fill" style={{ width: `${pct * 100}%`, height: 4, background: "var(--accent-dark)" }} />
                        </div>
                        <div style={{ fontSize: 9, color: missingCount > 0 ? "#b7791f" : "var(--text-muted)", marginTop: 2 }}>
                          {missingCount > 0 ? `⚠ ${missingCount} missing` : "✓ Complete"}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Candidate record list preview */}
                <div style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <h4 style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>Sample Candidates Preview (First 10)</h4>
                    <input
                      type="text"
                      placeholder="Search candidate ID or name..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      style={{
                        background: "var(--bg)",
                        border: "1px solid var(--border)",
                        borderRadius: 4,
                        padding: "4px 10px",
                        fontSize: 11,
                        color: "var(--text-primary)",
                        width: 220,
                      }}
                    />
                  </div>

                  <div style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: 6 }}>
                    <table className="data-table" style={{ width: "100%", tableLayout: "fixed" }}>
                      <thead>
                        <tr style={{ background: "var(--bg)" }}>
                          <th style={{ width: "120px" }}>ID</th>
                          <th style={{ width: "140px" }}>Anonymized Name</th>
                          <th style={{ width: "160px" }}>Current Title</th>
                          <th style={{ width: "80px" }}>YOE</th>
                          <th>Skills Profile Summary</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredSamples.length > 0 ? (
                          filteredSamples.map((cand: any, index: number) => (
                            <tr key={cand.candidate_id || index}>
                              <td style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-primary)" }}>{cand.candidate_id}</td>
                              <td style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{cand.profile?.anonymized_name || "Unknown"}</td>
                              <td style={{ fontSize: 11, color: "var(--text-secondary)" }}>{cand.profile?.current_title || "N/A"}</td>
                              <td style={{ fontSize: 11, color: "var(--text-primary)" }}>{cand.profile?.years_of_experience ?? "N/A"} yrs</td>
                              <td style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                {(cand.skills || []).slice(0, 4).map((s: any, idx: number) => (
                                  <span key={idx} className="skill-pill">
                                    {typeof s === "string" ? s : s.name}
                                  </span>
                                ))}
                                {(cand.skills || []).length > 4 && (
                                  <span style={{ fontSize: 10, color: "var(--text-muted)", marginLeft: 4 }}>
                                    +{cand.skills.length - 4} more
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)", fontSize: 11, padding: 16 }}>
                              No matching candidates found in the preview set.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Side-by-side JD and Schema previews */}
            <div style={{ display: "grid", gridTemplateColumns: (jdMetadata && schemaMetadata) ? "1fr 1fr" : "1fr", gap: 20 }}>
              {/* JD parsed requirements preview */}
              {jdMetadata && (
                <div className="card">
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", borderBottom: "1px solid var(--border)", paddingBottom: 10, marginBottom: 12 }}>
                    📋 Job Description Core Criteria
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "100px 1fr", fontSize: 12 }}>
                      <span style={{ color: "var(--text-muted)" }}>Target Role:</span>
                      <strong style={{ color: "var(--text-primary)" }}>{jdMetadata.job_title}</strong>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "100px 1fr", fontSize: 12 }}>
                      <span style={{ color: "var(--text-muted)" }}>Experience:</span>
                      <span style={{ color: "var(--text-primary)" }}>{jdMetadata.yoe_min} – {jdMetadata.yoe_max} Years</span>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "100px 1fr", fontSize: 12 }}>
                      <span style={{ color: "var(--text-muted)" }}>Location:</span>
                      <span style={{ color: "var(--text-primary)", textTransform: "capitalize" }}>{jdMetadata.location} ({jdMetadata.work_mode})</span>
                    </div>
                    
                    <div style={{ marginTop: 8 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                        Required Skills Profile:
                      </span>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {(jdMetadata.required_skills || []).map((skill: string) => (
                          <span key={skill} style={{ fontSize: 10, background: "rgba(183, 217, 178, 0.2)", color: "#1b5e20", padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div style={{ marginTop: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                        Nice-to-Have Skills:
                      </span>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {(jdMetadata.nice_to_have_skills || []).map((skill: string) => (
                          <span key={skill} style={{ fontSize: 10, background: "rgba(168, 197, 218, 0.2)", color: "#0d47a1", padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Schema properties list preview */}
              {schemaMetadata && (
                <div className="card">
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", borderBottom: "1px solid var(--border)", paddingBottom: 10, marginBottom: 12 }}>
                    🛡️ Schema Constraint Definition
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", fontSize: 12 }}>
                      <span style={{ color: "var(--text-muted)" }}>Schema Name:</span>
                      <strong style={{ color: "var(--text-primary)" }}>{schemaMetadata.title}</strong>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", fontSize: 12 }}>
                      <span style={{ color: "var(--text-muted)" }}>Total Properties:</span>
                      <span style={{ color: "var(--text-primary)" }}>{schemaMetadata.properties_count} defined fields</span>
                    </div>

                    <div style={{ marginTop: 8 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                        Root Validation Keys:
                      </span>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {(schemaMetadata.properties || []).map((prop: string) => {
                          const isRequired = (schemaMetadata.required_fields || []).includes(prop);
                          return (
                            <span
                              key={prop}
                              style={{
                                fontSize: 10,
                                background: isRequired ? "rgba(242, 214, 162, 0.2)" : "var(--bg)",
                                border: isRequired ? "1px solid #d97706" : "1px solid var(--border)",
                                color: isRequired ? "#b7791f" : "var(--text-secondary)",
                                padding: "2px 6px",
                                borderRadius: 4,
                                fontWeight: isRequired ? 600 : 500,
                              }}
                            >
                              {prop}{isRequired ? " *" : ""}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

          </div>
        )}

        {/* Action Button & Run Progress */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: 32 }}>
          <button
            onClick={handleRank}
            disabled={loading}
            style={{
              background: "var(--accent-dark)",
              color: "white",
              border: "none",
              borderRadius: 6,
              padding: "12px 48px",
              fontWeight: 600,
              fontSize: 14,
              cursor: "pointer",
              transition: "opacity 0.2s",
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "Processing Pipeline..." : "Run Ranking Cascade"}
          </button>
          
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 8 }}>
            {filesList.length > 0 
              ? "Executing ranking using the newly uploaded configurations."
              : "Uses default local candidate datasets and requirements config."}
          </div>

          {loading && (
            <div style={{ marginTop: 20, textAlign: "center" }}>
              <div className="spinner" style={{ margin: "0 auto 10px auto" }} />
              <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 500 }}>
                {loadingStage}
              </div>
            </div>
          )}

          {errorMessage && (
            <div style={{
              marginTop: 16,
              padding: "10px 20px",
              background: "#fff5f5",
              border: "1px solid #fecaca",
              borderRadius: 6,
              color: "#dc2626",
              fontSize: 12,
              fontWeight: 500,
            }}>
              ⚠️ {errorMessage}
            </div>
          )}
        </div>

        {/* Pipeline Results Overview */}
        {response && (
          <div>
            {/* Stats Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
              <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "center", padding: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>{response.total_candidates}</div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: 4 }}>Candidates Analyzed</div>
              </div>
              <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "center", padding: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>{response.results.length}</div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: 4 }}>Ranked Candidates</div>
              </div>
              <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "center", padding: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: response.malformed_candidates_count > 0 ? "#e11d48" : "var(--accent-dark)" }}>
                  {response.malformed_candidates_count}
                </div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: 4 }}>Malformed Profiles</div>
              </div>
              <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "center", padding: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>{response.validation_errors_count}</div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: 4 }}>Schema Anomalies</div>
              </div>
            </div>

            {/* Quick download card */}
            <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 24px", marginBottom: 28, background: "rgba(183, 217, 178, 0.08)", border: "1px solid var(--accent)" }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>Submission CSV Generated Successfully</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>Contains candidates ranking, normalized scores, and automated counterfactual justifications.</div>
              </div>
              <a
                href="http://127.0.0.1:8124/api/download"
                download="submission.csv"
                style={{
                  background: "var(--accent-dark)",
                  color: "white",
                  padding: "8px 16px",
                  borderRadius: 5,
                  fontSize: 12,
                  fontWeight: 600,
                  textDecoration: "none",
                }}
              >
                Download CSV
              </a>
            </div>

            {/* Layout grid for Ranked Candidates and Reports */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
              {/* Top 100 Candidates list */}
              <div className="card">
                <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "var(--text-primary)" }}>Top Ranked Profiles</h2>
                <div style={{ maxHeight: 600, overflowY: "auto" }}>
                  <table className="data-table" style={{ width: "100%" }}>
                    <thead>
                      <tr>
                        <th style={{ width: 40 }}>Rank</th>
                        <th>Profile</th>
                        <th style={{ width: 70 }}>Score</th>
                        <th style={{ width: 80 }}>Inspect</th>
                      </tr>
                    </thead>
                    <tbody>
                      {response.results.map((r) => (
                        <tr key={r.candidate_id} style={{ cursor: "pointer" }} onClick={() => inspectCandidate(r)}>
                          <td><span className="rank-badge">{r.rank}</span></td>
                          <td>
                            <div style={{ fontWeight: 600, fontSize: 12, color: "var(--text-primary)" }}>{r.name}</div>
                            <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{r.title}</div>
                          </td>
                          <td>
                            <span className={`score-badge ${r.score >= 0.85 ? "score-high" : r.score >= 0.70 ? "score-mid" : "score-low"}`} style={{ fontSize: 10 }}>
                              {(r.score * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td>
                            <button
                              onClick={(e) => { e.stopPropagation(); inspectCandidate(r); }}
                              style={{
                                border: "1px solid var(--border)",
                                borderRadius: 4,
                                background: "none",
                                fontSize: 10,
                                padding: "4px 8px",
                                cursor: "pointer",
                                color: "var(--text-secondary)"
                              }}
                            >
                              🔍 View
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Reports and verification analysis */}
              <div className="card">
                {/* Tabs */}
                <div style={{ display: "flex", borderBottom: "1px solid var(--border)", marginBottom: 16, overflowX: "auto" }}>
                  {[
                    { key: "schema_validation", label: "Schema Validation" },
                    { key: "ranking_audit", label: "Ranking Audit" },
                    { key: "honeypot_analysis", label: "Honeypot/Risk" },
                    { key: "distribution", label: "Distribution" },
                    { key: "hireability", label: "Hireability" },
                    { key: "feature_importance", label: "Feature Importance" },
                    { key: "ranking_diagnostics", label: "Diagnostics" },
                  ].map((tab) => (

                    <button
                      key={tab.key}
                      onClick={() => setSelectedReport(tab.key)}
                      style={{
                        padding: "10px 14px",
                        border: "none",
                        background: "none",
                        fontSize: 11,
                        fontWeight: selectedReport === tab.key ? 600 : 500,
                        color: selectedReport === tab.key ? "var(--accent-dark)" : "var(--text-muted)",
                        borderBottom: selectedReport === tab.key ? "2px solid var(--accent-dark)" : "none",
                        cursor: "pointer",
                        whiteSpace: "nowrap"
                      }}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div style={{ maxHeight: 600, overflowY: "auto", paddingRight: 8 }}>
                  <MarkdownRenderer text={response.reports[selectedReport] || ""} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Developer JSON Inspection Panel Drawer */}
        {inspectedCandidate && (
          <div
            style={{
              position: "fixed",
              top: 0,
              right: 0,
              width: 550,
              height: "100vh",
              background: "var(--card)",
              borderLeft: "1px solid var(--border)",
              boxShadow: "-4px 0 24px rgba(0, 0, 0, 0.15)",
              zIndex: 1000,
              display: "flex",
              flexDirection: "column",
              animation: "slideIn 0.3s ease-out forwards",
            }}
          >
            {/* Drawer Header */}
            <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>JSON Candidate Profiler</h3>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{inspectedCandidate.candidate_id}</div>
              </div>
              <button
                onClick={() => setInspectedCandidate(null)}
                style={{
                  border: "none",
                  background: "none",
                  fontSize: 20,
                  cursor: "pointer",
                  color: "var(--text-muted)",
                  padding: 4,
                }}
              >
                ✕
              </button>
            </div>

            {/* Drawer Content */}
            <div style={{ flex: 1, padding: 24, overflowY: "auto" }}>
              {/* Scores breakdown gauges */}
              <div style={{ marginBottom: 24 }}>
                <h4 style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", marginBottom: 12 }}>Feature Weights &amp; Outputs</h4>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  {[
                    { label: "Title Score", val: inspectedCandidate.score_breakdown.title_score },
                    { label: "Skills Score", val: inspectedCandidate.score_breakdown.skill_score },
                    { label: "Experience Score", val: inspectedCandidate.score_breakdown.experience_score },
                    { label: "Behavioral Score", val: inspectedCandidate.score_breakdown.behavioral_score },
                    { label: "Education Score", val: inspectedCandidate.score_breakdown.education_score },
                    { label: "GitHub Score", val: inspectedCandidate.score_breakdown.github_score },
                    { label: "Honeypot Prob", val: inspectedCandidate.score_breakdown.honeypot_probability, isRisk: true },
                    { label: "Final Score", val: inspectedCandidate.score, isFinal: true },
                  ].map((gauge, idx) => (
                    <div key={idx} style={{ background: "var(--bg)", padding: "8px 12px", borderRadius: 6, border: "1px solid var(--border)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-secondary)", marginBottom: 4 }}>
                        <span>{gauge.label}</span>
                        <span style={{ fontWeight: 600, color: gauge.isRisk && gauge.val > 0.4 ? "#dc2626" : "inherit" }}>{(gauge.val * 100).toFixed(1)}%</span>
                      </div>
                      <div className="progress-bar" style={{ height: 4 }}>
                        <div
                          className="progress-fill"
                          style={{
                            width: `${gauge.val * 100}%`,
                            background: gauge.isFinal ? "var(--accent-dark)" : (gauge.isRisk ? (gauge.val > 0.4 ? "#dc2626" : "#f59e0b") : "var(--accent)"),
                            height: 4,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Counterfactual description */}
              <div style={{ marginBottom: 24, padding: 14, background: "rgba(168, 197, 218, 0.06)", border: "1px solid var(--border)", borderRadius: 6 }}>
                <h4 style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--accent-dark)", marginBottom: 6 }}>Audit Reasoning</h4>
                <p style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {inspectedCandidate.reasoning}
                </p>
              </div>

              {/* JSON Editor/Viewer */}
              <div>
                <h4 style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", marginBottom: 8 }}>Raw Candidate JSON</h4>
                {loadingInspection ? (
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Loading raw profile data...</div>
                ) : (
                  <pre
                    style={{
                      background: "#1e1e2e",
                      color: "#cdd6f4",
                      padding: 16,
                      borderRadius: 8,
                      fontSize: 10.5,
                      fontFamily: "monospace",
                      overflowX: "auto",
                      maxHeight: 300,
                      border: "1px solid var(--border)",
                    }}
                  >
                    {JSON.stringify(inspectedCandidateData, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          </div>
        )}

      </main>

      {/* Slide-in animation helper */}
      <style jsx global>{`
        @keyframes slideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        .spinner {
          width: 24px;
          height: 24px;
          border: 3px solid var(--border);
          border-top-color: var(--accent-dark);
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

function MarkdownRenderer({ text }: { text: string }) {
  if (!text) return <div style={{ color: "var(--text-muted)", fontSize: 11 }}>No content available.</div>;

  const lines = text.split("\n");
  let inTable = false;
  let tableHeaders: string[] = [];
  let tableRows: string[][] = [];

  const elements: React.ReactNode[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Table parsing
    if (line.startsWith("|")) {
      const parts = line.split("|").map(p => p.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      if (line.includes("---") || line.includes(":---")) {
        continue;
      }
      if (!inTable) {
        inTable = true;
        tableHeaders = parts;
        tableRows = [];
      } else {
        tableRows.push(parts);
      }
      continue;
    } else {
      if (inTable) {
        const currentHeaders = [...tableHeaders];
        const currentRows = [...tableRows];
        elements.push(
          <div key={`table-${i}`} style={{ overflowX: "auto", margin: "14px 0" }}>
            <table className="data-table" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--bg)" }}>
                  {currentHeaders.map((h, idx) => (
                    <th key={idx} style={{ padding: "8px 10px", borderBottom: "2px solid var(--border)", textAlign: "left", fontSize: 11, color: "var(--text-secondary)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {currentRows.map((row, rIdx) => (
                  <tr key={rIdx} style={{ borderBottom: "1px solid var(--border)" }}>
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} style={{ padding: "8px 10px", fontSize: 11 }}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        inTable = false;
      }
    }

    if (!line) {
      continue;
    }

    // Headers
    if (line.startsWith("# ")) {
      elements.push(<h2 key={i} style={{ fontSize: 16, fontWeight: 700, margin: "20px 0 10px 0", color: "var(--text-primary)" }}>{line.slice(2)}</h2>);
    } else if (line.startsWith("## ")) {
      elements.push(<h3 key={i} style={{ fontSize: 14, fontWeight: 600, margin: "16px 0 8px 0", color: "var(--text-primary)" }}>{line.slice(3)}</h3>);
    } else if (line.startsWith("### ")) {
      elements.push(<h4 key={i} style={{ fontSize: 12, fontWeight: 600, margin: "12px 0 6px 0", color: "var(--text-primary)" }}>{line.slice(4)}</h4>);
    }
    // Lists
    else if (line.startsWith("- ") || line.startsWith("* ")) {
      elements.push(
        <ul key={i} style={{ margin: "4px 0 8px 20px", paddingLeft: 0, listStyleType: "disc" }}>
          <li style={{ fontSize: 11, color: "var(--text-secondary)" }}>{line.slice(2)}</li>
        </ul>
      );
    }
    // Check symbol / check box
    else if (line.startsWith("✓")) {
      elements.push(
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, margin: "10px 0", padding: "8px 12px", background: "rgba(183, 217, 178, 0.10)", borderRadius: 6, border: "1px solid var(--accent)", color: "var(--accent-dark)", fontSize: 11 }}>
          <span>✓</span>
          <span>{line.slice(2)}</span>
        </div>
      );
    }
    // Paragraph / Text
    else {
      let content: React.ReactNode = line;
      if (line.includes("**")) {
        const parts = line.split("**");
        content = parts.map((part, idx) => idx % 2 === 1 ? <strong key={idx} style={{ fontWeight: 600 }}>{part}</strong> : part);
      }
      elements.push(<p key={i} style={{ fontSize: 11.5, lineHeight: 1.5, color: "var(--text-secondary)", margin: "6px 0" }}>{content}</p>);
    }
  }

  if (inTable) {
    elements.push(
      <div key="table-end" style={{ overflowX: "auto", margin: "14px 0" }}>
        <table className="data-table" style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--bg)" }}>
              {tableHeaders.map((h, idx) => (
                <th key={idx} style={{ padding: "8px 10px", borderBottom: "2px solid var(--border)", textAlign: "left", fontSize: 11, color: "var(--text-secondary)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableRows.map((row, rIdx) => (
              <tr key={rIdx} style={{ borderBottom: "1px solid var(--border)" }}>
                {row.map((cell, cIdx) => (
                  <td key={cIdx} style={{ padding: "8px 10px", fontSize: 11 }}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return <div style={{ padding: "6px 0" }}>{elements}</div>;
}
