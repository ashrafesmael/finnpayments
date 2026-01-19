import React, { useState } from 'react'
import { analyzeEntityManual } from '../services/api'
import { Search, AlertCircle, AlertTriangle, CheckCircle, ExternalLink, Newspaper, ShieldCheck, XCircle, FileDown } from 'lucide-react'
import './ManualScreening.css'

const ManualScreening = () => {
  const [entityName, setEntityName] = useState('')
  const [entityType, setEntityType] = useState('individual')
  const [dateOfBirth, setDateOfBirth] = useState('')
  const [gender, setGender] = useState('')
  const [nationality, setNationality] = useState('')
  const [screeningProvider, setScreeningProvider] = useState('worldcheck')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // List of nationalities
  const nationalities = [
    "Afghan", "Albanian", "Algerian", "American", "Andorran", "Angolan", "Argentine", "Armenian", "Australian", "Austrian",
    "Azerbaijani", "Bahamian", "Bahraini", "Bangladeshi", "Barbadian", "Belarusian", "Belgian", "Belizean", "Beninese", "Bhutanese",
    "Bolivian", "Bosnian", "Brazilian", "British", "Bruneian", "Bulgarian", "Burkinabe", "Burmese", "Burundian", "Cambodian",
    "Cameroonian", "Canadian", "Cape Verdean", "Central African", "Chadian", "Chilean", "Chinese", "Colombian", "Comorian", "Congolese",
    "Costa Rican", "Croatian", "Cuban", "Cypriot", "Czech", "Danish", "Djiboutian", "Dominican", "Dutch", "Ecuadorian",
    "Egyptian", "Emirati", "Equatorial Guinean", "Eritrean", "Estonian", "Ethiopian", "Fijian", "Filipino", "Finnish", "French",
    "Gabonese", "Gambian", "Georgian", "German", "Ghanaian", "Greek", "Grenadian", "Guatemalan", "Guinean", "Guyanese",
    "Haitian", "Honduran", "Hungarian", "Icelandic", "Indian", "Indonesian", "Iranian", "Iraqi", "Irish", "Israeli",
    "Italian", "Ivorian", "Jamaican", "Japanese", "Jordanian", "Kazakh", "Kenyan", "Kuwaiti", "Kyrgyz", "Laotian",
    "Latvian", "Lebanese", "Liberian", "Libyan", "Lithuanian", "Luxembourgish", "Macedonian", "Malagasy", "Malawian", "Malaysian",
    "Maldivian", "Malian", "Maltese", "Mauritanian", "Mauritian", "Mexican", "Moldovan", "Monegasque", "Mongolian", "Montenegrin",
    "Moroccan", "Mozambican", "Namibian", "Nepalese", "New Zealander", "Nicaraguan", "Nigerian", "Nigerien", "North Korean", "Norwegian",
    "Omani", "Pakistani", "Panamanian", "Papua New Guinean", "Paraguayan", "Peruvian", "Polish", "Portuguese", "Qatari", "Romanian",
    "Russian", "Rwandan", "Saint Lucian", "Salvadoran", "Samoan", "Saudi", "Senegalese", "Serbian", "Seychellois", "Sierra Leonean",
    "Singaporean", "Slovak", "Slovenian", "Somali", "South African", "South Korean", "South Sudanese", "Spanish", "Sri Lankan", "Sudanese",
    "Surinamese", "Swedish", "Swiss", "Syrian", "Taiwanese", "Tajik", "Tanzanian", "Thai", "Togolese", "Trinidadian",
    "Tunisian", "Turkish", "Turkmen", "Ugandan", "Ukrainian", "Uruguayan", "Uzbek", "Venezuelan", "Vietnamese", "Yemeni",
    "Zambian", "Zimbabwean"
  ].sort()

  
  // Download PDF Report
  const downloadReport = async () => {
    if (!result?.analysis_id) return;
    
    try {
      const API_BASE = '/api' 
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

    if (!entityName.trim()) {
      setError('Please enter an entity name')
      return
    }

    try {
      setLoading(true)
      setError(null)
      // Build additional info object
      const additionalInfo = {}
      if (dateOfBirth) {
        // Convert dd/mm/yyyy to ISO format for backend
        const parts = dateOfBirth.split('/')
        if (parts.length === 3) {
          additionalInfo.date_of_birth = `${parts[2]}-${parts[1]}-${parts[0]}`
        }
      }
      if (gender) additionalInfo.gender = gender
      if (nationality) additionalInfo.nationality = nationality
      
      const data = await analyzeEntityManual(entityName, entityType, additionalInfo, screeningProvider)
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze entity')
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
    <div className="manual-screening">
      <div className="page-header">
        <h2>Manual Entity Screening</h2>
        <p>Screen individuals or organizations against sanctions lists, PEP databases, and adverse media</p>
      </div>

      <div className="screening-form-card">
        <form onSubmit={handleSubmit} className="screening-form">
          <div className="form-group">
            <label htmlFor="entityName">Entity Name *</label>
            <input
              type="text"
              id="entityName"
              value={entityName}
              onChange={(e) => setEntityName(e.target.value)}
              placeholder="e.g., John Smith, ABC Corporation"
              className="form-input"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="entityType">Entity Type</label>
            <select
              id="entityType"
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="form-select"
              disabled={loading}
            >
              <option value="individual">Individual</option>
              <option value="organization">Organization</option>
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="dateOfBirth">Date of Birth</label>
              <input
                type="text"
                id="dateOfBirth"
                value={dateOfBirth}
                onChange={(e) => setDateOfBirth(e.target.value)}
                placeholder="dd/mm/yyyy"
                className="form-input"
                disabled={loading}
              />
            </div>
            <div className="form-group">
              <label htmlFor="gender">Gender</label>
              <select
                id="gender"
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="form-select"
                disabled={loading}
              >
                <option value="">Select...</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="nationality">Country</label>
            <select
              id="nationality"
              value={nationality}
              onChange={(e) => setNationality(e.target.value)}
              className="form-select"
              disabled={loading}
            >
              <option value="">Select country...</option>
              <option value="Afghanistan">Afghanistan</option>
              <option value="Albania">Albania</option>
              <option value="Algeria">Algeria</option>
              <option value="Andorra">Andorra</option>
              <option value="Angola">Angola</option>
              <option value="Antigua and Barbuda">Antigua and Barbuda</option>
              <option value="Argentina">Argentina</option>
              <option value="Armenia">Armenia</option>
              <option value="Australia">Australia</option>
              <option value="Austria">Austria</option>
              <option value="Azerbaijan">Azerbaijan</option>
              <option value="Bahamas">Bahamas</option>
              <option value="Bahrain">Bahrain</option>
              <option value="Bangladesh">Bangladesh</option>
              <option value="Barbados">Barbados</option>
              <option value="Belarus">Belarus</option>
              <option value="Belgium">Belgium</option>
              <option value="Belize">Belize</option>
              <option value="Benin">Benin</option>
              <option value="Bhutan">Bhutan</option>
              <option value="Bolivia">Bolivia</option>
              <option value="Bosnia and Herzegovina">Bosnia and Herzegovina</option>
              <option value="Botswana">Botswana</option>
              <option value="Brazil">Brazil</option>
              <option value="Brunei">Brunei</option>
              <option value="Bulgaria">Bulgaria</option>
              <option value="Burkina Faso">Burkina Faso</option>
              <option value="Burundi">Burundi</option>
              <option value="Cambodia">Cambodia</option>
              <option value="Cameroon">Cameroon</option>
              <option value="Canada">Canada</option>
              <option value="Cape Verde">Cape Verde</option>
              <option value="Central African Republic">Central African Republic</option>
              <option value="Chad">Chad</option>
              <option value="Chile">Chile</option>
              <option value="China">China</option>
              <option value="Colombia">Colombia</option>
              <option value="Comoros">Comoros</option>
              <option value="Congo (Brazzaville)">Congo (Brazzaville)</option>
              <option value="Congo (DRC)">Congo (DRC)</option>
              <option value="Costa Rica">Costa Rica</option>
              <option value="Côte d'Ivoire">Côte d'Ivoire</option>
              <option value="Croatia">Croatia</option>
              <option value="Cuba">Cuba</option>
              <option value="Cyprus">Cyprus</option>
              <option value="Czech Republic">Czech Republic</option>
              <option value="Denmark">Denmark</option>
              <option value="Djibouti">Djibouti</option>
              <option value="Dominica">Dominica</option>
              <option value="Dominican Republic">Dominican Republic</option>
              <option value="Ecuador">Ecuador</option>
              <option value="Egypt">Egypt</option>
              <option value="El Salvador">El Salvador</option>
              <option value="Equatorial Guinea">Equatorial Guinea</option>
              <option value="Eritrea">Eritrea</option>
              <option value="Estonia">Estonia</option>
              <option value="Eswatini">Eswatini</option>
              <option value="Ethiopia">Ethiopia</option>
              <option value="Fiji">Fiji</option>
              <option value="Finland">Finland</option>
              <option value="France">France</option>
              <option value="Gabon">Gabon</option>
              <option value="Gambia">Gambia</option>
              <option value="Georgia">Georgia</option>
              <option value="Germany">Germany</option>
              <option value="Ghana">Ghana</option>
              <option value="Greece">Greece</option>
              <option value="Grenada">Grenada</option>
              <option value="Guatemala">Guatemala</option>
              <option value="Guinea">Guinea</option>
              <option value="Guinea-Bissau">Guinea-Bissau</option>
              <option value="Guyana">Guyana</option>
              <option value="Haiti">Haiti</option>
              <option value="Honduras">Honduras</option>
              <option value="Hungary">Hungary</option>
              <option value="Iceland">Iceland</option>
              <option value="India">India</option>
              <option value="Indonesia">Indonesia</option>
              <option value="Iran">Iran</option>
              <option value="Iraq">Iraq</option>
              <option value="Ireland">Ireland</option>
              <option value="Israel">Israel</option>
              <option value="Italy">Italy</option>
              <option value="Jamaica">Jamaica</option>
              <option value="Japan">Japan</option>
              <option value="Jordan">Jordan</option>
              <option value="Kazakhstan">Kazakhstan</option>
              <option value="Kenya">Kenya</option>
              <option value="Kiribati">Kiribati</option>
              <option value="Kosovo">Kosovo</option>
              <option value="Kuwait">Kuwait</option>
              <option value="Kyrgyzstan">Kyrgyzstan</option>
              <option value="Laos">Laos</option>
              <option value="Latvia">Latvia</option>
              <option value="Lebanon">Lebanon</option>
              <option value="Lesotho">Lesotho</option>
              <option value="Liberia">Liberia</option>
              <option value="Libya">Libya</option>
              <option value="Liechtenstein">Liechtenstein</option>
              <option value="Lithuania">Lithuania</option>
              <option value="Luxembourg">Luxembourg</option>
              <option value="Madagascar">Madagascar</option>
              <option value="Malawi">Malawi</option>
              <option value="Malaysia">Malaysia</option>
              <option value="Maldives">Maldives</option>
              <option value="Mali">Mali</option>
              <option value="Malta">Malta</option>
              <option value="Marshall Islands">Marshall Islands</option>
              <option value="Mauritania">Mauritania</option>
              <option value="Mauritius">Mauritius</option>
              <option value="Mexico">Mexico</option>
              <option value="Micronesia">Micronesia</option>
              <option value="Moldova">Moldova</option>
              <option value="Monaco">Monaco</option>
              <option value="Mongolia">Mongolia</option>
              <option value="Montenegro">Montenegro</option>
              <option value="Morocco">Morocco</option>
              <option value="Mozambique">Mozambique</option>
              <option value="Myanmar">Myanmar</option>
              <option value="Namibia">Namibia</option>
              <option value="Nauru">Nauru</option>
              <option value="Nepal">Nepal</option>
              <option value="Netherlands">Netherlands</option>
              <option value="New Zealand">New Zealand</option>
              <option value="Nicaragua">Nicaragua</option>
              <option value="Niger">Niger</option>
              <option value="Nigeria">Nigeria</option>
              <option value="North Korea">North Korea</option>
              <option value="North Macedonia">North Macedonia</option>
              <option value="Norway">Norway</option>
              <option value="Oman">Oman</option>
              <option value="Pakistan">Pakistan</option>
              <option value="Palau">Palau</option>
              <option value="Palestine">Palestine</option>
              <option value="Panama">Panama</option>
              <option value="Papua New Guinea">Papua New Guinea</option>
              <option value="Paraguay">Paraguay</option>
              <option value="Peru">Peru</option>
              <option value="Philippines">Philippines</option>
              <option value="Poland">Poland</option>
              <option value="Portugal">Portugal</option>
              <option value="Qatar">Qatar</option>
              <option value="Romania">Romania</option>
              <option value="Russia">Russia</option>
              <option value="Rwanda">Rwanda</option>
              <option value="Saint Kitts and Nevis">Saint Kitts and Nevis</option>
              <option value="Saint Lucia">Saint Lucia</option>
              <option value="Saint Vincent and the Grenadines">Saint Vincent and the Grenadines</option>
              <option value="Samoa">Samoa</option>
              <option value="San Marino">San Marino</option>
              <option value="Sao Tome and Principe">Sao Tome and Principe</option>
              <option value="Saudi Arabia">Saudi Arabia</option>
              <option value="Senegal">Senegal</option>
              <option value="Serbia">Serbia</option>
              <option value="Seychelles">Seychelles</option>
              <option value="Sierra Leone">Sierra Leone</option>
              <option value="Singapore">Singapore</option>
              <option value="Slovakia">Slovakia</option>
              <option value="Slovenia">Slovenia</option>
              <option value="Solomon Islands">Solomon Islands</option>
              <option value="Somalia">Somalia</option>
              <option value="South Africa">South Africa</option>
              <option value="South Korea">South Korea</option>
              <option value="South Sudan">South Sudan</option>
              <option value="Spain">Spain</option>
              <option value="Sri Lanka">Sri Lanka</option>
              <option value="Sudan">Sudan</option>
              <option value="Suriname">Suriname</option>
              <option value="Sweden">Sweden</option>
              <option value="Switzerland">Switzerland</option>
              <option value="Syria">Syria</option>
              <option value="Taiwan">Taiwan</option>
              <option value="Tajikistan">Tajikistan</option>
              <option value="Tanzania">Tanzania</option>
              <option value="Thailand">Thailand</option>
              <option value="Timor-Leste">Timor-Leste</option>
              <option value="Togo">Togo</option>
              <option value="Tonga">Tonga</option>
              <option value="Trinidad and Tobago">Trinidad and Tobago</option>
              <option value="Tunisia">Tunisia</option>
              <option value="Turkey">Turkey</option>
              <option value="Turkmenistan">Turkmenistan</option>
              <option value="Tuvalu">Tuvalu</option>
              <option value="Uganda">Uganda</option>
              <option value="Ukraine">Ukraine</option>
              <option value="United Arab Emirates">United Arab Emirates</option>
              <option value="United Kingdom">United Kingdom</option>
              <option value="United States">United States</option>
              <option value="Uruguay">Uruguay</option>
              <option value="Uzbekistan">Uzbekistan</option>
              <option value="Vanuatu">Vanuatu</option>
              <option value="Vatican City">Vatican City</option>
              <option value="Venezuela">Venezuela</option>
              <option value="Vietnam">Vietnam</option>
              <option value="Yemen">Yemen</option>
              <option value="Zambia">Zambia</option>
              <option value="Zimbabwe">Zimbabwe</option>
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
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? (
              <>
                <div className="btn-spinner"></div>
                Analyzing...
              </>
            ) : (
              <>
                <Search size={20} />
                Screen Entity
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
            <h3>Screening Results</h3>
            <span className="analysis-id">ID: {result.analysis_id}</span>
          </div>

          <div className="result-summary">
            <div className="summary-item">
              <label>Entity Name</label>
              <p>{result.entity_name}</p>
            </div>
            <div className="summary-item">
              <label>Entity Type</label>
              <p className="capitalize">{result.entity_type}</p>
            </div>
            <div className="summary-item">
              <label>Processing Time</label>
              <p>{result.processing_time_ms}ms</p>
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

          <div className="risk-overview">
            <div className="risk-score-card" style={{ borderColor: getRiskColor(result.risk_level) }}>
              <div className="risk-score-value" style={{ color: getRiskColor(result.risk_level) }}>
                {result.risk_score.toFixed(1)}
              </div>
              <div className="risk-score-label">Risk Score</div>
              <div className="risk-level-badge" style={{
                background: getRiskColor(result.risk_level) + '20',
                color: getRiskColor(result.risk_level)
              }}>
                {result.risk_level}
              </div>
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
                    <td className={result.sanctions_risk > 50 ? 'score-high' : ''}>{result.sanctions_risk.toFixed(1)}%</td>
                    <td>85%</td>
                    <td>{(result.sanctions_risk * 0.85).toFixed(1)}</td>
                  </tr>
                  <tr>
                    <td>PEP Risk</td>
                    <td className={result.pep_risk > 50 ? 'score-medium' : ''}>{result.pep_risk.toFixed(1)}%</td>
                    <td>30%</td>
                    <td>{(result.pep_risk * 0.30).toFixed(1)}</td>
                  </tr>
                  <tr>
                    <td>Adverse Media Risk</td>
                    <td className={result.adverse_media_risk > 50 ? 'score-medium' : ''}>{result.adverse_media_risk.toFixed(1)}%</td>
                    <td>20%</td>
                    <td>{(result.adverse_media_risk * 0.20).toFixed(1)}</td>
                  </tr>
                  <tr>
                    <td>Jurisdiction Risk</td>
                    <td>{(result.jurisdiction_risk || 0).toFixed(1)}%</td>
                    <td>20%</td>
                    <td>{((result.jurisdiction_risk || 0) * 0.20).toFixed(1)}</td>
                  </tr>
                </tbody>
              </table>

              <div className="risk-item">
                <span>Sanctions Risk</span>
                <div className="risk-bar">
                  <div
                    className="risk-bar-fill"
                    style={{ width: `${result.sanctions_risk}%`, background: '#ef4444' }}
                  ></div>
                </div>
                <span className="risk-value">{result.sanctions_risk.toFixed(1)}%</span>
              </div>
              <div className="risk-item">
                <span>PEP Risk</span>
                <div className="risk-bar">
                  <div
                    className="risk-bar-fill"
                    style={{ width: `${result.pep_risk}%`, background: '#f59e0b' }}
                  ></div>
                </div>
                <span className="risk-value">{result.pep_risk.toFixed(1)}%</span>
              </div>
              <div className="risk-item">
                <span>Adverse Media Risk</span>
                <div className="risk-bar">
                  <div
                    className="risk-bar-fill"
                    style={{ width: `${result.adverse_media_risk}%`, background: '#f97316' }}
                  ></div>
                </div>
                <span className="risk-value">{result.adverse_media_risk.toFixed(1)}%</span>
              </div>
              <div className="risk-item">
                <span>Jurisdiction Risk</span>
                <div className="risk-bar">
                  <div
                    className="risk-bar-fill"
                    style={{ width: `${result.jurisdiction_risk || 0}%`, background: '#8b5cf6' }}
                  ></div>
                </div>
                <span className="risk-value">{(result.jurisdiction_risk || 0).toFixed(1)}%</span>
              </div>
              {/* Behavioral Risk hidden until transactional data screening is implemented
              <div className="risk-item">
                <span>Behavioral Risk</span>
                <div className="risk-bar">
                  <div
                    className="risk-bar-fill"
                    style={{ width: `${result.behavioral_risk || 0}%`, background: '#06b6d4' }}
                  ></div>
                </div>
                <span className="risk-value">{(result.behavioral_risk || 0).toFixed(1)}%</span>
              </div>
              */}
            </div>
          </div>

          {/* Positive Findings / Screening Checks Section */}
          {result.positive_findings && (
            <div className="positive-findings-section">
              <h4>
                <ShieldCheck size={18} />
                Screening Checks Performed
              </h4>
              
              {result.positive_findings.dilisense_matches?.fallback_used && (
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
                    <strong>Fallback Provider Used:</strong> {result.positive_findings.dilisense_matches.requested_provider === 'dilisense' ? 'Dilisense' : 'World Check One'} was unavailable. 
                    Results are from {result.positive_findings.dilisense_matches.actual_provider === 'worldcheck' ? 'World Check One' : 'Dilisense'}.
                  </span>
                </div>
              )}
              <div className="checks-grid">
                {result.positive_findings.checks_performed?.map((check, idx) => (
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

              {result.positive_findings.overall_clear && (
                <div className="overall-clear-badge">
                  <CheckCircle size={20} />
                  <span>All screening checks passed - Entity appears clear</span>
                </div>
              )}
            </div>
          )}

          {result.flags && result.flags.length > 0 && (
            <div className="flags-section">
              <h4>Risk Flags</h4>
              <div className="flags-list">
                {result.flags.map((flag, index) => (
                  <div key={index} className="flag-item">
                    <AlertCircle size={16} />
                    {flag}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sanctions Match Results Section */}
          {result.positive_findings?.sanctions_matches && result.positive_findings.sanctions_matches.matches?.length > 0 && (
            <div className="sanctions-matches-section">
              <h4>
                <AlertTriangle size={18} />
                Global Sanctions List Matches
              </h4>
              <div className="sanctions-summary">
                <div className="match-stat">
                  <span className="stat-value">{result.positive_findings.sanctions_matches.matches.length}</span>
                  <span className="stat-label">Matches Found</span>
                </div>
                <div className="lists-checked">
                  <span className="lists-label">Lists Checked:</span>
                  <div className="lists-tags">
                    {result.positive_findings.sanctions_matches.lists_checked?.map((list, idx) => (
                      <span key={idx} className="list-tag">{list}</span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="sanctions-records">
                <h5>Match Details</h5>
                {result.positive_findings.sanctions_matches.matches.map((match, idx) => (
                  <div key={idx} className="sanctions-record">
                    <div className="record-header">
                      <span className="record-source">{match.source}</span>
                      {match.confidence && (
                        <span className={`confidence-badge ${match.confidence.toLowerCase()}`}>
                          {match.confidence} Confidence
                        </span>
                      )}
                    </div>
                    <p className="record-snippet">{match.snippet}</p>
                    {match.link && (
                      <a href={match.link} target="_blank" rel="noopener noreferrer" className="record-link">
                        <ExternalLink size={14} />
                        View Source
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* World-Check One Matches Section - Only show if World-Check was used */}
          {result.positive_findings?.dilisense_matches && 
           result.positive_findings.dilisense_matches.total_hits > 0 && 
           result.positive_findings.dilisense_matches.provider?.includes('World Check') && (
            <div className="worldcheck-matches-section">
              <h4>
                <AlertTriangle size={18} />
                World-Check One Database Matches
              </h4>
              <div className="worldcheck-summary">
                <div className="match-stats">
                  <div className="match-stat">
                    <span className="stat-value">{result.positive_findings.dilisense_matches.total_hits}</span>
                    <span className="stat-label">Total Matches</span>
                  </div>
                  {result.positive_findings.dilisense_matches.sanctions_hits > 0 && (
                    <div className="match-stat sanctions">
                      <span className="stat-value">{result.positive_findings.dilisense_matches.sanctions_hits}</span>
                      <span className="stat-label">Sanctions</span>
                    </div>
                  )}
                  {result.positive_findings.dilisense_matches.pep_hits > 0 && (
                    <div className="match-stat pep">
                      <span className="stat-value">{result.positive_findings.dilisense_matches.pep_hits}</span>
                      <span className="stat-label">PEP</span>
                    </div>
                  )}
                  {result.positive_findings.dilisense_matches.special_interest_hits > 0 && (
                    <div className="match-stat special-interest">
                      <span className="stat-value">{result.positive_findings.dilisense_matches.special_interest_hits}</span>
                      <span className="stat-label">Special Interest</span>
                    </div>
                  )}
                </div>
              </div>
              {result.positive_findings.dilisense_matches.records?.length > 0 && (
                <div className="worldcheck-records">
                  <h5>Match Details</h5>
                  {result.positive_findings.dilisense_matches.records.map((record, idx) => (
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
          {result.positive_findings?.dilisense_matches && 
           result.positive_findings.dilisense_matches.total_hits > 0 && 
           (result.positive_findings.dilisense_matches.provider?.includes('Dilisense') || 
            !result.positive_findings.dilisense_matches.provider) && (
            <div className="dilisense-matches-section">
              <h4>
                <AlertTriangle size={18} />
                Dilisense Screening Matches
              </h4>
              <div className="dilisense-summary">
                <div className="match-stats">
                  <div className="match-stat">
                    <span className="stat-value">{result.positive_findings.dilisense_matches.total_hits}</span>
                    <span className="stat-label">Total Matches</span>
                  </div>
                  {result.positive_findings.dilisense_matches.sanctions_hits > 0 && (
                    <div className="match-stat sanctions">
                      <span className="stat-value">{result.positive_findings.dilisense_matches.sanctions_hits}</span>
                      <span className="stat-label">Sanctions</span>
                    </div>
                  )}
                  {result.positive_findings.dilisense_matches.pep_hits > 0 && (
                    <div className="match-stat pep">
                      <span className="stat-value">{result.positive_findings.dilisense_matches.pep_hits}</span>
                      <span className="stat-label">PEP</span>
                    </div>
                  )}
                  {result.positive_findings.dilisense_matches.special_interest_hits > 0 && (
                    <div className="match-stat special-interest">
                      <span className="stat-value">{result.positive_findings.dilisense_matches.special_interest_hits}</span>
                      <span className="stat-label">Special Interest</span>
                    </div>
                  )}
                  {result.positive_findings.dilisense_matches.criminal_hits > 0 && (
                    <div className="match-stat criminal">
                      <span className="stat-value">{result.positive_findings.dilisense_matches.criminal_hits}</span>
                      <span className="stat-label">Criminal</span>
                    </div>
                  )}
                </div>
              </div>
              {result.positive_findings.dilisense_matches.records?.length > 0 && (
                <div className="dilisense-records">
                  <h5>Match Details</h5>
                  {result.positive_findings.dilisense_matches.records.map((record, idx) => (
                    <div key={idx} className="dilisense-record">
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
          {result.positive_findings?.dilisense_matches?.pep_hits > 0 && 
           (result.positive_findings.dilisense_matches.provider?.includes('Dilisense') || 
            !result.positive_findings.dilisense_matches.provider) && (
            <div className="pep-findings-section">
              <h4>
                <AlertTriangle size={18} />
                PEP (Politically Exposed Person) Findings
              </h4>
              <div className="pep-summary">
                <div className="pep-alert">
                  <span className="alert-icon">⚠</span>
                  <span className="alert-text">
                    {result.positive_findings.dilisense_matches.pep_hits} PEP match(es) found
                  </span>
                </div>
              </div>
              {result.positive_findings.dilisense_matches.records?.filter(r => 
                r.source_type?.toUpperCase() === 'PEP' || r.match_type?.toUpperCase()?.includes('PEP')
              ).length > 0 && (
                <div className="pep-records">
                  <h5>PEP Match Details</h5>
                  {result.positive_findings.dilisense_matches.records
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
          {result.positive_findings?.dilisense_matches?.sanctions_hits > 0 && 
           (result.positive_findings.dilisense_matches.provider?.includes('Dilisense') || 
            !result.positive_findings.dilisense_matches.provider) && (
            <div className="sanctions-findings-section">
              <h4>
                <AlertTriangle size={18} />
                Sanctions List Matches
              </h4>
              <div className="sanctions-summary">
                <div className="sanctions-alert critical">
                  <span className="alert-icon">🚨</span>
                  <span className="alert-text">
                    CRITICAL: {result.positive_findings.dilisense_matches.sanctions_hits} match(es) found on official sanctions lists
                  </span>
                </div>
              </div>
              {result.positive_findings.dilisense_matches.records?.filter(r => 
                r.source_type?.toUpperCase() === 'SANCTION' || r.match_type?.toUpperCase()?.includes('SANCTION')
              ).length > 0 && (
                <div className="sanctions-records">
                  <h5>Sanctions Match Details</h5>
                  {result.positive_findings.dilisense_matches.records
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
          {result.adverse_media_findings && (
            <div className="adverse-media-section">
              <h4>
                <Newspaper size={18} />
                Media Findings
              </h4>
              
              {result.adverse_media_findings.total_mentions > 0 ? (
                <>
                  <div className="adverse-media-summary">
                    <div className="media-stat">
                      <span className="stat-value">{result.adverse_media_findings.total_mentions}</span>
                      <span className="stat-label">Mentions Found</span>
                    </div>
                    {result.adverse_media_findings.risk_keywords_found?.length > 0 && (
                      <div className="risk-keywords">
                        <span className="keywords-label">Risk Keywords:</span>
                        <div className="keywords-list">
                          {result.adverse_media_findings.risk_keywords_found.map((keyword, idx) => (
                            <span key={idx} className="keyword-tag">{keyword}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {result.adverse_media_findings.articles?.length > 0 && (
                    <div className="articles-list">
                      <h5>Related Articles</h5>
                      {result.adverse_media_findings.articles.map((article, idx) => (
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

          {result.recommendations && result.recommendations.length > 0 && (
            <div className="recommendations-section">
              <h4>Recommendations</h4>
              <div className="recommendations-list">
                {result.recommendations.map((rec, index) => (
                  <div key={index} className="recommendation-item">
                    <CheckCircle size={16} />
                    {rec}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ManualScreening
