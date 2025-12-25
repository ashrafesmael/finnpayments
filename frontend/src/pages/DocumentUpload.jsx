import React, { useState } from 'react'
import { uploadDocument } from '../services/api'
import { Upload, FileText, AlertCircle, AlertTriangle, CheckCircle, ExternalLink, Newspaper, ShieldCheck, XCircle, FileDown } from 'lucide-react'
import './DocumentUpload.css'

const DocumentUpload = () => {
  const [file, setFile] = useState(null)
  const [documentType, setDocumentType] = useState('')
  const [screeningProvider, setScreeningProvider] = useState('worldcheck')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
      setError(null)
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setError(null)
    }
  }


  // Download PDF Report
  const downloadReport = async () => {
    if (!result?.analysis_id) return;
    
    try {
      const API_BASE = '/api'; // Fixed 
      const response = await fetch(`${API_BASE}/report/${result.analysis_id}`);
      if (!response.ok) throw new Error('Failed to generate report');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `finnverify_report_${result.analysis_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Report download failed:', err);
      alert('Failed to download report. Please try again.');
    }
  };

    const handleSubmit = async (e) => {
    e.preventDefault()

    if (!file) {
      setError('Please select a file to upload')
      return
    }

    try {
      setLoading(true)
      setError(null)
      const data = await uploadDocument(file, documentType || null, screeningProvider)
      setResult(data)
      setFile(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload document')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getRiskColor = (level) => {
    const colors = {
      LOW: '#10b981',
      MEDIUM: '#f59e0b',
      HIGH: '#f97316',
      CRITICAL: '#ef4444'
    }
    return colors[level] || '#6b7280'
  }

  const getStatusIcon = (status) => {
    if (status === 'clear') {
      return <CheckCircle size={18} color="#10b981" />
    }
    return <XCircle size={18} color="#ef4444" />
  }

  const getStatusColor = (status) => {
    return status === 'clear' ? '#10b981' : '#ef4444'
  }

  return (
    <div className="document-upload">
      <div className="page-header">
        <h2>Document Upload & Analysis</h2>
        <p>Upload SAR, KYC documents, or transaction records for automated analysis</p>
      </div>

      <div className="upload-form-card">
        <form onSubmit={handleSubmit}>
          <div
            className={`file-drop-zone ${dragActive ? 'active' : ''} ${file ? 'has-file' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {file ? (
              <div className="file-preview">
                <FileText size={48} />
                <p className="file-name">{file.name}</p>
                <p className="file-size">{(file.size / 1024).toFixed(2)} KB</p>
                <button
                  type="button"
                  className="btn-remove"
                  onClick={() => setFile(null)}
                >
                  Remove
                </button>
              </div>
            ) : (
              <>
                <Upload size={48} />
                <p className="drop-text">Drag & drop your file here</p>
                <p className="drop-subtext">or</p>
                <label htmlFor="file-input" className="btn btn-secondary">
                  Browse Files
                </label>
                <input
                  id="file-input"
                  type="file"
                  onChange={handleFileChange}
                  accept=".pdf,.png,.jpg,.jpeg,.docx,.doc,.txt,.csv,.xlsx,.xls"
                  style={{ display: 'none' }}
                />
                <p className="supported-formats">
                  Supported: PDF, Images, Word, CSV, Excel
                </p>
              </>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="documentType">Document Type (Optional)</label>
            <select
              id="documentType"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              className="form-select"
              disabled={loading}
            >
              <option value="">Auto-detect</option>
              <option value="SAR">Suspicious Activity Report (SAR)</option>
              <option value="TRANSACTION">Transaction Record</option>
              <option value="KYC">KYC Document</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="screeningProvider">Screening Provider</label>
            <select
              id="screeningProvider"
              value={screeningProvider}
              onChange={(e) => setScreeningProvider(e.target.value)}
              className="form-select"
              disabled={loading}
            >
              <option value="worldcheck">World Check One Screening</option>
              <option value="dilisense">Dilisense Screening</option>
            </select>
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={loading || !file}
          >
            {loading ? (
              <>
                <div className="btn-spinner"></div>
                Analyzing Document...
              </>
            ) : (
              <>
                <Upload size={20} />
                Upload & Analyze
              </>
            )}
          </button>
        </form>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      {result && (
        <div className="result-card">
          <div className="result-header">
            <h3>Analysis Results</h3>
            <span className="analysis-id">ID: {result.analysis_id}</span>
          </div>

          <div className="result-summary">
            <div className="summary-item">
              <label>Document Type</label>
              <p>{result.document_type}</p>
            </div>
            <div className="summary-item">
              <label>Processing Time</label>
              <p>{result.processing_time_ms}ms</p>
            </div>
            <div className="summary-item">
              <label>Timestamp</label>
              <p>{new Date(result.timestamp).toLocaleString()}</p>
            </div>
            <div className="summary-item download-section">
              <button 
                onClick={downloadReport}
                className="download-report-btn"
                title="Download PDF Report"
              >
                <FileDown size={18} />
                Download Report
              </button>
            </div>
          </div>

          {result.extracted_data && (
            <div className="extracted-data-section">
              <h4>Extracted Data</h4>
              <div className="data-grid">
                {Object.entries(result.extracted_data)
                  .filter(([key]) => !['report_id', 'filing_date', 'filing_institution', 'subject_name', 
                    'subject_account', 'transaction_amount', 'transaction_date', 'suspicious_activity_type',
                    'narrative', 'transaction_id', 'originator_name', 'originator_account', 
                    'beneficiary_name', 'beneficiary_account', 'amount', 'currency', 'purpose'].includes(key))
                  .map(([key, value]) => (
                  <div key={key} className="data-item">
                    <label>{key.replace(/_/g, ' ').toUpperCase()}</label>
                    {key === 'confidence_scores' && typeof value === 'object' ? (
                      <div className="confidence-scores">
                        {Object.entries(value).map(([field, score]) => (
                          <div key={field} className="confidence-item">
                            <span className="confidence-field">{field.replace(/_/g, ' ')}</span>
                            <div className="confidence-bar">
                              <div 
                                className="confidence-fill" 
                                style={{ 
                                  width: `${(score * 100)}%`,
                                  background: score >= 0.9 ? '#10b981' : score >= 0.7 ? '#f59e0b' : '#ef4444'
                                }}
                              ></div>
                            </div>
                            <span className="confidence-value">{(score * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.risk_assessment && (
            <div className="risk-assessment-section">
              <h4>Risk Assessment</h4>
              <div className="risk-summary">
                <div className="risk-score-display" style={{
                  borderColor: getRiskColor(result.risk_assessment.risk_level)
                }}>
                  <div className="score-value" style={{
                    color: getRiskColor(result.risk_assessment.risk_level)
                  }}>
                    {result.risk_assessment.final_risk_score.toFixed(1)}
                  </div>
                  <div className="score-label">Risk Score</div>
                  <span className="risk-badge" style={{
                    background: getRiskColor(result.risk_assessment.risk_level) + '20',
                    color: getRiskColor(result.risk_assessment.risk_level)
                  }}>
                    {result.risk_assessment.risk_level}
                  </span>
                </div>

                <div className="risk-breakdown">
                  <h4>Risk Breakdown</h4>
                  
                  {/* Risk Score Table */}
                  <table className="risk-table">
                    <thead>
                      <tr>
                        <th>Risk Category</th>
                        <th>Score</th>
                        <th>Weight</th>
                        <th>Weighted Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Sanctions Risk</td>
                        <td className={result.risk_assessment.sanctions_risk > 50 ? 'score-high' : ''}>{result.risk_assessment.sanctions_risk.toFixed(1)}%</td>
                        <td>85%</td>
                        <td>{(result.risk_assessment.sanctions_risk * 0.85).toFixed(1)}</td>
                      </tr>
                      <tr>
                        <td>PEP Risk</td>
                        <td className={result.risk_assessment.pep_risk > 50 ? 'score-medium' : ''}>{result.risk_assessment.pep_risk.toFixed(1)}%</td>
                        <td>30%</td>
                        <td>{(result.risk_assessment.pep_risk * 0.30).toFixed(1)}</td>
                      </tr>
                      <tr>
                        <td>Adverse Media Risk</td>
                        <td className={result.risk_assessment.adverse_media_risk > 50 ? 'score-medium' : ''}>{result.risk_assessment.adverse_media_risk.toFixed(1)}%</td>
                        <td>20%</td>
                        <td>{(result.risk_assessment.adverse_media_risk * 0.20).toFixed(1)}</td>
                      </tr>
                      <tr>
                        <td>Jurisdiction Risk</td>
                        <td>{(result.risk_assessment.jurisdiction_risk || 0).toFixed(1)}%</td>
                        <td>20%</td>
                        <td>{((result.risk_assessment.jurisdiction_risk || 0) * 0.20).toFixed(1)}</td>
                      </tr>
                    </tbody>
                  </table>

                  <div className="risk-item">
                    <span>Sanctions Risk</span>
                    <div className="risk-bar">
                      <div
                        className="risk-bar-fill"
                        style={{ width: `${result.risk_assessment.sanctions_risk}%`, background: '#ef4444' }}
                      ></div>
                    </div>
                    <span className="risk-value">{result.risk_assessment.sanctions_risk.toFixed(1)}%</span>
                  </div>
                  <div className="risk-item">
                    <span>PEP Risk</span>
                    <div className="risk-bar">
                      <div
                        className="risk-bar-fill"
                        style={{ width: `${result.risk_assessment.pep_risk}%`, background: '#f59e0b' }}
                      ></div>
                    </div>
                    <span className="risk-value">{result.risk_assessment.pep_risk.toFixed(1)}%</span>
                  </div>
                  <div className="risk-item">
                    <span>Adverse Media Risk</span>
                    <div className="risk-bar">
                      <div
                        className="risk-bar-fill"
                        style={{ width: `${result.risk_assessment.adverse_media_risk}%`, background: '#f97316' }}
                      ></div>
                    </div>
                    <span className="risk-value">{result.risk_assessment.adverse_media_risk.toFixed(1)}%</span>
                  </div>
                  <div className="risk-item">
                    <span>Jurisdiction Risk</span>
                    <div className="risk-bar">
                      <div
                        className="risk-bar-fill"
                        style={{ width: `${result.risk_assessment.jurisdiction_risk || 0}%`, background: '#8b5cf6' }}
                      ></div>
                    </div>
                    <span className="risk-value">{(result.risk_assessment.jurisdiction_risk || 0).toFixed(1)}%</span>
                  </div>
                </div>
              </div>

              {result.risk_assessment.flags && result.risk_assessment.flags.length > 0 && (
                <div className="flags-list">
                  <h5>Risk Flags</h5>
                  {result.risk_assessment.flags.map((flag, index) => (
                    <div key={index} className="flag-item">
                      <AlertCircle size={16} />
                      {flag}
                    </div>
                  ))}
                </div>
              )}

              {/* Positive Findings / Screening Checks Section */}
              {result.risk_assessment.positive_findings && (
                <div className="positive-findings-section">
                  <h5>
                    <ShieldCheck size={18} />
                    Screening Checks Performed
                  </h5>
                  {result.risk_assessment.positive_findings.dilisense_matches?.fallback_used && (
                    <div style={{
                      background: '#fef3c7',
                      border: '1px solid #f59e0b',
                      borderRadius: '8px',
                      padding: '12px 16px',
                      marginBottom: '16px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px'
                    }}>
                      <AlertTriangle size={18} color="#f59e0b" />
                      <span style={{ color: '#92400e', fontSize: '14px' }}>
                        <strong>Fallback Provider Used:</strong> {result.risk_assessment.positive_findings.dilisense_matches.requested_provider === 'dilisense' ? 'Dilisense' : 'World Check One'} was unavailable. 
                        Results are from {result.risk_assessment.positive_findings.dilisense_matches.actual_provider === 'worldcheck' ? 'World Check One' : 'Dilisense'}.
                      </span>
                    </div>
                  )}
                  <div className="checks-grid">
                    {result.risk_assessment.positive_findings.checks_performed?.map((check, idx) => (
                      <div key={idx} className={`check-item ${check.status === 'clear' ? 'clear' : 'alert'}`}>
                        <div className="check-header">
                          {getStatusIcon(check.status)}
                          <span className="check-source">{check.source}</span>
                        </div>
                        <div className="check-details" style={{ color: getStatusColor(check.status) }}>
                          {check.details}
                        </div>
                      </div>
                    ))}
                  </div>

                  {result.risk_assessment.positive_findings.overall_clear && (
                    <div className="overall-clear-badge">
                      <CheckCircle size={20} />
                      <span>All screening checks passed - Entity appears clear</span>
                    </div>
                  )}
                </div>
              )}

              {/* World-Check One Matches Section - Only show if World-Check was used */}
              {result.risk_assessment.positive_findings?.dilisense_matches && 
               result.risk_assessment.positive_findings.dilisense_matches.total_hits > 0 && 
               result.risk_assessment.positive_findings.dilisense_matches.provider?.includes('World-Check') && (
                <div className="worldcheck-matches-section">
                  <h5>
                    <AlertTriangle size={18} />
                    World-Check One Database Matches
                  </h5>
                  <div className="worldcheck-summary">
                    <div className="match-stats">
                      <div className="match-stat">
                        <span className="stat-value">{result.risk_assessment.positive_findings.dilisense_matches.total_hits}</span>
                        <span className="stat-label">Total Matches</span>
                      </div>
                      {result.risk_assessment.positive_findings.dilisense_matches.sanctions_hits > 0 && (
                        <div className="match-stat sanctions">
                          <span className="stat-value">{result.risk_assessment.positive_findings.dilisense_matches.sanctions_hits}</span>
                          <span className="stat-label">Sanctions</span>
                        </div>
                      )}
                      {result.risk_assessment.positive_findings.dilisense_matches.pep_hits > 0 && (
                        <div className="match-stat pep">
                          <span className="stat-value">{result.risk_assessment.positive_findings.dilisense_matches.pep_hits}</span>
                          <span className="stat-label">PEP</span>
                        </div>
                      )}
                      {result.risk_assessment.positive_findings.dilisense_matches.special_interest_hits > 0 && (
                        <div className="match-stat special-interest">
                          <span className="stat-value">{result.risk_assessment.positive_findings.dilisense_matches.special_interest_hits}</span>
                          <span className="stat-label">Special Interest</span>
                        </div>
                      )}
                    </div>
                  </div>
                  {result.risk_assessment.positive_findings.dilisense_matches.records?.length > 0 && (
                    <div className="worldcheck-records">
                      <h5>Match Details</h5>
                      {result.risk_assessment.positive_findings.dilisense_matches.records.map((record, idx) => (
                        <div key={idx} className="worldcheck-record">
                          <div className="record-header">
                            <span className="record-name">{record.name}</span>
                            <div className="record-badges">
                              <span className={`match-type ${record.match_type?.toLowerCase()}`}>
                                {record.match_type} ({record.match_score}%)
                              </span>
                              <span className={`record-type ${record.source_type?.toLowerCase()}`}>
                                {record.source_type}
                              </span>
                            </div>
                          </div>
                          {record.positions?.length > 0 && (
                            <div className="record-positions">
                              {record.positions.map((pos, pidx) => (
                                <span key={pidx} className="position-tag">{pos}</span>
                              ))}
                            </div>
                          )}
                          {record.countries?.length > 0 && (
                            <div className="record-countries">
                              <strong>Countries:</strong> {record.countries.join(', ')}
                            </div>
                          )}
                          {record.reference_id && (
                            <div className="record-reference">
                              <strong>Reference ID:</strong> {record.reference_id}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Dilisense AML Matches Section - Only show if Dilisense was used */}
              {result.risk_assessment.positive_findings?.dilisense_matches && 
               result.risk_assessment.positive_findings.dilisense_matches.total_hits > 0 && 
               (result.risk_assessment.positive_findings.dilisense_matches.provider?.includes('Dilisense') || 
                !result.risk_assessment.positive_findings.dilisense_matches.provider) && (
                <div className="dilisense-matches-section">
                  <h5>
                    <AlertTriangle size={18} />
                    Dilisense Screening Matches
                  </h5>
                  <div className="dilisense-summary">
                    <div className="match-stats">
                      <div className="match-stat">
                        <span className="stat-value">{result.risk_assessment.positive_findings.dilisense_matches.total_hits}</span>
                        <span className="stat-label">Total Matches</span>
                      </div>
                      {result.risk_assessment.positive_findings.dilisense_matches.sanctions_hits > 0 && (
                        <div className="match-stat sanctions">
                          <span className="stat-value">{result.risk_assessment.positive_findings.dilisense_matches.sanctions_hits}</span>
                          <span className="stat-label">Sanctions</span>
                        </div>
                      )}
                      {result.risk_assessment.positive_findings.dilisense_matches.pep_hits > 0 && (
                        <div className="match-stat pep">
                          <span className="stat-value">{result.risk_assessment.positive_findings.dilisense_matches.pep_hits}</span>
                          <span className="stat-label">PEP</span>
                        </div>
                      )}
                      {result.risk_assessment.positive_findings.dilisense_matches.special_interest_hits > 0 && (
                        <div className="match-stat special-interest">
                          <span className="stat-value">{result.risk_assessment.positive_findings.dilisense_matches.special_interest_hits}</span>
                          <span className="stat-label">Special Interest</span>
                        </div>
                      )}
                      {result.risk_assessment.positive_findings.dilisense_matches.criminal_hits > 0 && (
                        <div className="match-stat criminal">
                          <span className="stat-value">{result.risk_assessment.positive_findings.dilisense_matches.criminal_hits}</span>
                          <span className="stat-label">Criminal</span>
                        </div>
                      )}
                    </div>
                  </div>
                  {result.risk_assessment.positive_findings.dilisense_matches.records?.length > 0 && (
                    <div className="dilisense-records">
                      <h6>Match Details</h6>
                      {result.risk_assessment.positive_findings.dilisense_matches.records.map((record, idx) => (
                        <div key={idx} className="dilisense-record">
                          <div className="record-header">
                            <span className="record-name">{record.name}</span>
                            <div className="record-badges">
                              {record.match_type && (
                                <span className={`match-type ${record.match_type?.toLowerCase()}`}>
                                  {record.match_type} {record.match_score ? `(${record.match_score}%)` : ''}
                                </span>
                              )}
                              <span className={`record-type ${record.source_type?.toLowerCase()}`}>
                                {record.source_type}
                              </span>
                            </div>
                          </div>
                          {record.searched_name && record.searched_name !== record.name && (
                            <div className="searched-name">
                              Searched: <strong>{record.searched_name}</strong> → Matched: <strong>{record.name}</strong>
                            </div>
                          )}
                          {record.positions?.length > 0 && (
                            <div className="record-positions">
                              {record.positions.map((pos, pidx) => (
                                <span key={pidx} className="position-tag">{pos}</span>
                              ))}
                            </div>
                          )}
                          {record.sanction_details && (
                            <p className="sanction-details">{record.sanction_details}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* PEP Findings Section */}
              {result.risk_assessment.positive_findings?.dilisense_matches?.pep_hits > 0 && (
                <div className="pep-findings-section">
                  <h5>
                    <AlertTriangle size={18} />
                    PEP (Politically Exposed Person) Findings
                  </h5>
                  <div className="pep-summary">
                    <div className="pep-alert">
                      <span className="alert-icon">⚠</span>
                      <span className="alert-text">
                        {result.risk_assessment.positive_findings.dilisense_matches.pep_hits} PEP match(es) found
                      </span>
                    </div>
                  </div>
                  {result.risk_assessment.positive_findings.dilisense_matches.records?.filter(r => 
                    r.source_type?.toUpperCase() === 'PEP' || r.match_type?.toUpperCase()?.includes('PEP')
                  ).length > 0 && (
                    <div className="pep-records">
                      <h6>PEP Match Details</h6>
                      {result.risk_assessment.positive_findings.dilisense_matches.records
                        .filter(r => r.source_type?.toUpperCase() === 'PEP' || r.match_type?.toUpperCase()?.includes('PEP'))
                        .map((record, idx) => (
                          <div key={idx} className="pep-record">
                            <div className="record-header">
                              <span className="record-name">{record.name}</span>
                              <span className="match-score">{record.match_score}% match</span>
                            </div>
                            {record.positions?.length > 0 && (
                              <div className="record-positions">
                                <strong>Positions:</strong> {record.positions.join(', ')}
                              </div>
                            )}
                            {record.countries?.length > 0 && (
                              <div className="record-countries">
                                <strong>Countries:</strong> {Array.isArray(record.countries) ? record.countries.join(', ') : record.countries}
                              </div>
                            )}
                            {record.sanction_details && (
                              <p className="record-details">{record.sanction_details}</p>
                            )}
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              )}

              {/* Sanctions Findings Section */}
              {result.risk_assessment.positive_findings?.dilisense_matches?.sanctions_hits > 0 && (
                <div className="sanctions-findings-section">
                  <h5>
                    <AlertTriangle size={18} />
                    Sanctions List Matches
                  </h5>
                  <div className="sanctions-summary">
                    <div className="sanctions-alert critical">
                      <span className="alert-icon">🚨</span>
                      <span className="alert-text">
                        CRITICAL: {result.risk_assessment.positive_findings.dilisense_matches.sanctions_hits} match(es) found on official sanctions lists
                      </span>
                    </div>
                  </div>
                  {result.risk_assessment.positive_findings.dilisense_matches.records?.filter(r => 
                    r.source_type?.toUpperCase() === 'SANCTION' || r.match_type?.toUpperCase()?.includes('SANCTION')
                  ).length > 0 && (
                    <div className="sanctions-records">
                      <h6>Sanctions Match Details</h6>
                      {result.risk_assessment.positive_findings.dilisense_matches.records
                        .filter(r => r.source_type?.toUpperCase() === 'SANCTION' || r.match_type?.toUpperCase()?.includes('SANCTION'))
                        .map((record, idx) => (
                          <div key={idx} className="sanctions-record">
                            <div className="record-header">
                              <span className="record-name">{record.name}</span>
                              <span className="match-score">{record.match_score}% match</span>
                            </div>
                            {record.sources?.length > 0 && (
                              <div className="record-sources">
                                <strong>Sanctions Lists:</strong> {Array.isArray(record.sources) ? record.sources.join(', ') : record.sources}
                              </div>
                            )}
                            {record.countries?.length > 0 && (
                              <div className="record-countries">
                                <strong>Countries:</strong> {Array.isArray(record.countries) ? record.countries.join(', ') : record.countries}
                              </div>
                            )}
                            {record.entity_type && (
                              <div className="record-entity-type">
                                <strong>Entity Type:</strong> {record.entity_type}
                              </div>
                            )}
                            {record.sanction_details && (
                              <p className="record-details">{record.sanction_details}</p>
                            )}
                          </div>
                        ))}
                    </div>
                  )}
                  <div className="sanctions-warning">
                    <strong>⚠ IMPORTANT:</strong> Sanctions matches require immediate review. Do not proceed with any business relationship until sanctions status is verified and cleared.
                  </div>
                </div>
              )}

              {/* Media Findings Section */}
              {result.risk_assessment.adverse_media_findings && (
                <div className="adverse-media-section">
                  <h5>
                    <Newspaper size={18} />
                    Media Findings
                  </h5>
                  
                  {result.risk_assessment.adverse_media_findings.total_mentions > 0 ? (
                    <>
                      <div className="adverse-media-summary">
                        <div className="media-stat">
                          <span className="stat-value">{result.risk_assessment.adverse_media_findings.total_mentions}</span>
                          <span className="stat-label">Mentions Found</span>
                        </div>
                        {result.risk_assessment.adverse_media_findings.risk_keywords_found?.length > 0 && (
                          <div className="risk-keywords">
                            <span className="keywords-label">Risk Keywords:</span>
                            <div className="keywords-list">
                              {result.risk_assessment.adverse_media_findings.risk_keywords_found.map((keyword, idx) => (
                                <span key={idx} className="keyword-tag">{keyword}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {result.risk_assessment.adverse_media_findings.articles?.length > 0 && (
                        <div className="articles-list">
                          <h6>Related Articles</h6>
                          {result.risk_assessment.adverse_media_findings.articles.map((article, idx) => (
                            <div key={idx} className="article-item">
                              <div className="article-title">
                                {article.link ? (
                                  <a href={article.link} target="_blank" rel="noopener noreferrer">
                                    {article.title}
                                    <ExternalLink size={14} />
                                  </a>
                                ) : (
                                  article.title
                                )}
                              </div>
                              {article.snippet && (
                                <p className="article-snippet">{article.snippet}</p>
                              )}
                              <span className="article-source">{article.source}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="no-adverse-media">
                      <CheckCircle size={20} color="#10b981" />
                      <span>No adverse media mentions found</span>
                    </div>
                  )}
                </div>
              )}

              {result.risk_assessment.recommendations && result.risk_assessment.recommendations.length > 0 && (
                <div className="recommendations-list">
                  <h5>Recommendations</h5>
                  {result.risk_assessment.recommendations.map((rec, index) => (
                    <div key={index} className="recommendation-item">
                      <CheckCircle size={16} />
                      {rec}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default DocumentUpload
