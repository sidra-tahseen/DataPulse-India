
import { useCallback, useEffect, useState } from 'react'
import {
  getDatasets,
  getLatestHealthReport,
  getHealthHistory,
  getHealthComparison,
  getMonitorStatus,
  getHealthTrends,
  getReliability,
  getMandiPriceHistory,
  getMandiPriceChanges,
  runMonitor,
} from './api'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'

function formatDate(value) {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function formatRecordIdentifier(record, datasetId) {
  const item = record?.record_id ?? record ?? {}
  const fields = datasetId === 'mandi_prices'
    ? ['commodity', 'market', 'arrival_date', 'state']
    : ['cityname', 'month_year']

  return fields
    .map((field) => item[field])
    .filter((value) => value !== null && value !== undefined && value !== '')
    .join(' · ') || '—'
}

function App() {
  const [datasets, setDatasets] = useState([])
  const [selectedDataset, setSelectedDataset] = useState('rainfall_surat')
  const [report, setReport] = useState(null)
  const [history, setHistory] = useState([])
  const [comparison, setComparison] = useState(null)
  const [monitorStatus, setMonitorStatus] = useState(null)
  const [trends, setTrends] = useState([])
  const [reliability, setReliability] = useState(null)
  const [reliabilityError, setReliabilityError] = useState('')
  const [mandiPriceHistory, setMandiPriceHistory] = useState([])
  const [priceHistoryLimit, setPriceHistoryLimit] = useState(10)
  const [reportHistoryLimit, setReportHistoryLimit] = useState(10)
  const [mandiPriceChanges, setMandiPriceChanges] = useState([])
  const [mandiPricesError, setMandiPricesError] = useState('')
  const [trendsError, setTrendsError] = useState('')
  const [lastDashboardRefresh, setLastDashboardRefresh] = useState(null)

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [runningMonitor, setRunningMonitor] = useState(false)

  const [error, setError] = useState('')
  const [comparisonError, setComparisonError] = useState('')
  const [monitorMessage, setMonitorMessage] = useState('')

  const loadDashboard = useCallback(async (isRefresh = false, datasetId = selectedDataset) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    setError('')
    setComparisonError('')

    try {
      const [latest, pastReports, status] = await Promise.all([
        getLatestHealthReport(datasetId),
        getHealthHistory(datasetId),
        getMonitorStatus(),
      ])

      setReport(latest)
      setHistory(pastReports.history ?? [])
      setMonitorStatus(status)

      if (datasetId === 'mandi_prices') {
        try {
          const [priceHistoryResult, priceChangesResult] = await Promise.all([
            getMandiPriceHistory(100),
            getMandiPriceChanges(100),
          ])
          setMandiPriceHistory(priceHistoryResult.observations ?? [])
          setMandiPriceChanges(priceChangesResult.changes ?? [])
          setMandiPricesError('')
        } catch (priceErr) {
          setMandiPriceHistory([])
          setMandiPriceChanges([])
          setMandiPricesError(
            priceErr.message || 'Could not load mandi price history.',
          )
        }
      } else {
        setMandiPriceHistory([])
        setMandiPriceChanges([])
        setMandiPricesError('')
      }

      try {
        const reliabilityResult = await getReliability(datasetId)
        setReliability(reliabilityResult.metrics ?? {})
        setReliabilityError('')
      } catch (reliabilityErr) {
        setReliability(null)
        setReliabilityError(
          reliabilityErr.message || 'Could not load API reliability metrics.',
        )
      }

      try {
        const trendResult = await getHealthTrends(datasetId)
        setTrends(trendResult.trends ?? [])
        setTrendsError('')
      } catch (trendErr) {
        setTrends([])
        setTrendsError(
          trendErr.message || 'Could not load historical trend data.',
        )
      }

      try {
        const comparisonResult = await getHealthComparison(datasetId)
        setComparison(comparisonResult)
      } catch (err) {
        setComparison(null)
        setComparisonError(
          err.message || 'Could not load health comparison.',
        )
      }

      setLastDashboardRefresh(new Date())
    } catch (err) {
      setError(err.message || 'Could not load dashboard data.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [selectedDataset])

  // Load available datasets and refresh the selected dataset every 30 seconds.
  useEffect(() => {
    getDatasets()
      .then((items) => setDatasets(items))
      .catch((err) => setError(err.message || 'Could not load datasets.'))
  }, [])

  useEffect(() => {
    loadDashboard(false, selectedDataset)

    const timer = setInterval(() => {
      loadDashboard(true, selectedDataset)
    }, 30_000)

    return () => clearInterval(timer)
  }, [loadDashboard, selectedDataset])

  async function handleRunMonitor() {
    setRunningMonitor(true)
    setMonitorMessage('')
    setError('')

    try {
      const result = await runMonitor(selectedDataset)

      setMonitorMessage(
        result.message || 'Monitoring completed successfully.',
      )

      await loadDashboard(true, selectedDataset)
    } catch (err) {
      setError(err.message || 'Monitoring run failed.')
    } finally {
      setRunningMonitor(false)
    }
  }

  const changeRecordFields = selectedDataset === 'mandi_prices'
    ? [
        { key: 'commodity', label: 'Commodity' },
        { key: 'market', label: 'Market' },
        { key: 'arrival_date', label: 'Arrival date' },
        { key: 'state', label: 'State' },
      ]
    : [
        { key: 'cityname', label: 'City' },
        { key: 'month_year', label: 'Month / year' },
      ]

  const metrics = report?.health_metrics ?? {}

  const completeness = Number(metrics.completeness_percent ?? 0)
  const missingValues = Number(metrics.missing_values ?? 0)
  const missingByField = metrics.missing_by_field ?? {}
  const schemaValid = metrics.schema_valid
  const freshness = metrics.freshness_status ?? 'UNKNOWN'
  const ageDays = metrics.age_days

  const reliabilityData = reliability ?? {}
  const totalRequests = reliabilityData.total_requests ?? reliabilityData.total_attempts ?? reliabilityData.request_count ?? reliabilityData.total ?? 0
  const successfulRequests = reliabilityData.successful_requests ?? reliabilityData.success_count ?? reliabilityData.successes ?? reliabilityData.successful ?? 0
  const failedRequests = reliabilityData.failed_requests ?? reliabilityData.failure_count ?? reliabilityData.failures ?? reliabilityData.failed ?? 0
  const successRate = reliabilityData.success_rate_percent ?? reliabilityData.success_rate ?? reliabilityData.success_rate_pct
  const averageResponseTime = reliabilityData.average_duration_ms ?? reliabilityData.avg_duration_ms ?? reliabilityData.average_response_time_ms ?? reliabilityData.mean_duration_ms
  const displayedSuccessRate = successRate ?? (Number(totalRequests) > 0 ? (Number(successfulRequests) / Number(totalRequests)) * 100 : null)

  const freshnessClass =
    freshness === 'FRESH'
      ? 'success-text'
      : freshness === 'STALE'
        ? 'warning-text'
        : 'neutral-text'

  const schemaClass =
    schemaValid === true
      ? 'success-text'
      : schemaValid === false
        ? 'warning-text'
        : 'neutral-text'

  const schedulerRunning = monitorStatus?.running === true
  const lastRunFailed = monitorStatus?.last_result === 'FAILED'

  return (
    <div className="app-shell">
      <style>{`
        .app-shell { align-items: start; }
        .sidebar {
          position: sticky;
          top: 0;
          height: 100vh;
          align-self: start;
          overflow-y: auto;
          z-index: 20;
        }
        @media (max-width: 760px) {
          .sidebar {
            position: sticky;
            top: 0;
            height: auto;
            max-height: 45vh;
          }
        }
        .report-history-summary {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
          cursor: pointer;
          list-style: none;
          padding: 0.5rem 0;
        }
        .report-history-summary::-webkit-details-marker { display: none; }
        .report-history-summary::after {
          content: '+';
          color: #e8a0b5;
          font-size: 1.5rem;
          margin-left: 0.5rem;
        }
        .report-history-details[open] .report-history-summary::after { content: '−'; }
        .report-history-summary h3 { margin: 0.25rem 0; }
        .report-history-controls {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 0.75rem;
          margin: 1rem 0;
        }
        .report-history-controls label { color: #b7a9bd; font-size: 0.875rem; }
        .report-history-controls select {
          background: #241d2b;
          color: #f4eaf2;
          border: 1px solid rgba(220, 190, 220, 0.3);
          border-radius: 2px;
          padding: 0.5rem 0.75rem;
          font: inherit;
        }
        .report-history-controls .panel-footnote { margin: 0; }
        @media (max-width: 640px) { .report-history-summary { align-items: flex-start; } }
      `}</style>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">DP</div>
          <div>
            <h2>DataPulse</h2>
            <p>INDIA</p>
          </div>
        </div>

        <p className="nav-label">MONITORING</p>

        <nav>
          <a className="nav-item active" href="#overview">
            Overview
          </a>
          <a className="nav-item" href="#quality">
            Data quality
          </a>
          <a className="nav-item" href="#changes">
            Change detection
          </a>
          <a className="nav-item" href="#prices">
            Mandi prices
          </a>
          <a className="nav-item" href="#trends">
            Historical trends
          </a>
          <a className="nav-item" href="#history">
            Report history
          </a>
        </nav>

        <div className="sidebar-bottom">
          <span className="status-dot" />
          <div>
            <p>DATA OBSERVABILITY</p>
            <span>Public data · India</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <div className="topbar">
          <span>DATA OBSERVABILITY / INDIA</span>
          <span className="environment">LIVE MONITORING</span>
        </div>

        <header className="page-heading" id="overview">
          <div>
            <h1>Dataset health overview</h1>
            <p className="subtitle">
              Monitor data quality, freshness and changes across public datasets.
            </p>
          </div>

          <button
            className="run-button"
            onClick={handleRunMonitor}
            disabled={runningMonitor || schedulerRunning}
          >
            {runningMonitor || schedulerRunning
              ? 'Running monitor...'
              : 'Run monitor'}
            <span>↗</span>
          </button>
        </header>

        <div className="header-actions dataset-selector-row">
          <label htmlFor="dataset-select" className="field-label">SELECT DATASET</label>
          <select
            id="dataset-select"
            value={selectedDataset}
            onChange={(event) => {
              setSelectedDataset(event.target.value)
              setMonitorMessage('')
            }}
            aria-label="Select dataset to monitor"
          >
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name}
              </option>
            ))}
          </select>
          <button
            className="secondary-button"
            onClick={() => loadDashboard(true, selectedDataset)}
            disabled={refreshing || loading}
          >
            {refreshing ? 'Refreshing...' : 'Refresh data'}
          </button>
          <span className="panel-footnote">Auto-refresh: every 30 seconds</span>
        </div>


        {error && (
          <div className="notice">
            <span className="notice-marker" />
            <div>
              <strong>Unable to load dashboard</strong>
              <p>{error}</p>
            </div>
          </div>
        )}

        {monitorMessage && (
          <div className="notice">
            <span className="notice-marker" />
            <div>
              <strong>Monitoring update</strong>
              <p>{monitorMessage}</p>
            </div>
          </div>
        )}

        {monitorStatus && (
          <section className="panel quality-panel live-status-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">AUTOMATED INGESTION</p>
                <h3>Live monitoring status</h3>
              </div>
              <span
                className={`check-result ${
                  schedulerRunning
                    ? 'warning-text'
                    : lastRunFailed
                      ? 'warning-text'
                      : 'success-text'
                }`}
              >
                {schedulerRunning
                  ? 'RUNNING'
                  : lastRunFailed
                    ? 'LAST RUN FAILED'
                    : monitorStatus.last_result === 'SUCCESS'
                      ? 'OPERATIONAL'
                      : 'WAITING'}
              </span>
            </div>

            <div className="record-stats">
              <div>
                <span className="field-label">CHECK INTERVAL</span>
                <h3>
                  Every {monitorStatus.schedule_interval_minutes ?? 15} min
                </h3>
              </div>

              <div>
                <span className="field-label">LAST RUN STARTED</span>
                <h3>
                  {formatDate(monitorStatus.last_started_at)}
                </h3>
              </div>

              <div>
                <span className="field-label">LAST RUN COMPLETED</span>
                <h3>
                  {formatDate(monitorStatus.last_completed_at)}
                </h3>
              </div>

              <div>
                <span className="field-label">NEXT SCHEDULED CHECK</span>
                <h3>
                  {formatDate(monitorStatus.next_scheduled_run)}
                </h3>
              </div>
            </div>

            {lastRunFailed && monitorStatus.last_error && (
              <div className="notice">
                <span className="notice-marker" />
                <div>
                  <strong>Latest monitoring run failed</strong>
                  <p>{monitorStatus.last_error}</p>
                </div>
              </div>
            )}

            <p className="panel-footnote">
              Dashboard refreshes every 30 seconds. Source data changes only
              when the publisher updates the dataset. The timestamps above
              describe monitoring runs, not necessarily source publication time.
            </p>

            <p className="panel-footnote">
              Dashboard last refreshed: {formatDate(lastDashboardRefresh)}
            </p>
          </section>
        )}

        {loading ? (
          <section className="panel quality-panel">
            <p>Loading dataset health information...</p>
          </section>
        ) : !report ? (
          <section className="panel quality-panel">
            <h3>No monitoring report available</h3>
            <p className="subtitle">
              Run the monitor to generate the first health report.
            </p>
          </section>
        ) : (
          <>
            <section className="dataset-strip">
              <div>
                <span className="field-label">CURRENT DATASET</span>
                <h3>{report.dataset ?? 'Unknown dataset'}</h3>
              </div>

              <div>
                <span className="field-label">LAST CHECKED</span>
                <p>{formatDate(report.checked_at)}</p>
              </div>

              <div>
                <span className="field-label">SOURCE FRESHNESS</span>
                <p className={freshnessClass}>{freshness}</p>
              </div>
            </section>

            <section className="metrics-grid">
              <article className="metric-card">
                <div className="metric-top">
                  <span>COMPLETENESS</span>
                  <span className="metric-indicator warning" />
                </div>
                <h2>{completeness.toFixed(1)}%</h2>
                <p>Records with complete values</p>
              </article>

              <article className="metric-card">
                <div className="metric-top">
                  <span>MISSING VALUES</span>
                  <span className="metric-indicator warning" />
                </div>
                <h2>{missingValues}</h2>
                <p>Missing field values detected</p>
              </article>

              <article className="metric-card">
                <div className="metric-top">
                  <span>SCHEMA VALIDATION</span>
                  <span
                    className={`metric-indicator ${
                      schemaValid === true
                        ? 'success'
                        : schemaValid === false
                          ? 'warning'
                          : 'neutral'
                    }`}
                  />
                </div>
                <h2>
                  {schemaValid === true
                    ? 'Valid'
                    : schemaValid === false
                      ? 'Invalid'
                      : 'Unknown'}
                </h2>
                <p>Required fields and structure</p>
              </article>

              <article className="metric-card">
                <div className="metric-top">
                  <span>SOURCE AGE</span>
                  <span className="metric-indicator neutral" />
                </div>
                <h2>
                  {ageDays === null || ageDays === undefined
                    ? 'Unknown'
                    : `${ageDays} days`}
                </h2>
                <p>Age based on source update information</p>
              </article>
            </section>

            <section className="panel history-panel reliability-panel" id="reliability">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">API OBSERVABILITY</p>
                  <h3>Ingestion reliability</h3>
                </div>
                <span className="small-tag">{selectedDataset === 'rainfall_surat' ? 'RAINFALL' : selectedDataset === 'mandi_prices' ? 'MANDI' : 'SELECTED DATASET'}</span>
              </div>

              <p className="panel-footnote">
                Request metrics for the selected dataset, including retries recorded by the ingestion layer.
              </p>

              {reliabilityError ? (
                <p className="panel-footnote">{reliabilityError}</p>
              ) : (
                <div className="metrics-grid reliability-metrics-grid">
                  <article className="metric-card">
                    <div className="metric-top">
                      <span>REQUEST SUCCESS RATE</span>
                      <span className="metric-indicator success" />
                    </div>
                    <h2>{displayedSuccessRate == null ? '—' : `${Number(displayedSuccessRate).toFixed(1)}%`}</h2>
                    <p>Successful requests as a share of recorded requests</p>
                  </article>

                  <article className="metric-card">
                    <div className="metric-top">
                      <span>AVERAGE RESPONSE TIME</span>
                      <span className="metric-indicator neutral" />
                    </div>
                    <h2>{averageResponseTime == null ? '—' : `${Number(averageResponseTime).toFixed(0)} ms`}</h2>
                    <p>Average duration of recorded API requests</p>
                  </article>

                  <article className="metric-card">
                    <div className="metric-top">
                      <span>RECORDED REQUESTS</span>
                      <span className="metric-indicator neutral" />
                    </div>
                    <h2>{totalRequests}</h2>
                    <p>Request attempts recorded for this dataset</p>
                  </article>

                  <article className="metric-card">
                    <div className="metric-top">
                      <span>FAILED REQUESTS</span>
                      <span className={`metric-indicator ${Number(failedRequests) > 0 ? 'warning' : 'success'}`} />
                    </div>
                    <h2>{failedRequests}</h2>
                    <p>Failed attempts recorded by the API client</p>
                  </article>
                </div>
              )}
              <p className="panel-footnote">
                These metrics reflect requests recorded since reliability logging began; they are not a live uptime guarantee.
              </p>
            </section>

            {selectedDataset === 'mandi_prices' && (
              <section className="panel history-panel" id="prices">
                <details className="price-history-details">
                  <summary className="price-history-summary">
                    <div>
                      <p className="eyebrow">AGRICULTURAL MARKET DATA</p>
                      <h3>Mandi price history</h3>
                      <p className="panel-footnote">
                        Expand to view saved modal prices and choose how many rows to display.
                      </p>
                    </div>
                    <span className="small-tag">
                      {mandiPriceHistory.length} OBSERVATIONS
                    </span>
                  </summary>

                  <div className="price-history-controls">
                    <label htmlFor="price-history-limit">Rows to display</label>
                    <select
                      id="price-history-limit"
                      value={priceHistoryLimit}
                      onChange={(event) =>
                        setPriceHistoryLimit(Number(event.target.value))
                      }
                    >
                      <option value={10}>10 rows</option>
                      <option value={25}>25 rows</option>
                      <option value={50}>50 rows</option>
                      <option value={100}>100 rows</option>
                    </select>
                    <span className="panel-footnote">
                      Showing {Math.min(priceHistoryLimit, mandiPriceHistory.length)} of {mandiPriceHistory.length} observations
                    </span>
                  </div>

                  {mandiPricesError ? (
                    <p className="panel-footnote">{mandiPricesError}</p>
                  ) : mandiPriceHistory.length > 0 ? (
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Commodity</th>
                            <th>State</th>
                            <th>District</th>
                            <th>Market</th>
                            <th>Arrival date</th>
                            <th>Modal price</th>
                            <th>Observed at</th>
                          </tr>
                        </thead>
                        <tbody>
                          {mandiPriceHistory
                            .slice(0, priceHistoryLimit)
                            .map((item, index) => (
                              <tr
                                key={`${item.state}-${item.market}-${item.commodity}-${item.arrival_date}-${item.observed_at}-${index}`}
                              >
                                <td>{item.commodity ?? '—'}</td>
                                <td>{item.state ?? '—'}</td>
                                <td>{item.district ?? '—'}</td>
                                <td>{item.market ?? '—'}</td>
                                <td>{item.arrival_date ?? '—'}</td>
                                <td>
                                  {item.modal_price == null
                                    ? '—'
                                    : `₹${Number(item.modal_price).toLocaleString('en-IN')}`}
                                </td>
                                <td>{formatDate(item.observed_at)}</td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="panel-footnote">
                      No saved mandi price observations are available yet. Run the mandi price monitor to collect data.
                    </p>
                  )}
                </details>

                <div className="record-change-details">
                  <div className="panel-heading">
                    <div>
                      <p className="eyebrow">PRICE MOVEMENT TRACKER</p>
                      <h3>Detected price changes</h3>
                    </div>
                    <span className="small-tag">{mandiPriceChanges.length} CHANGES</span>
                  </div>

                  {mandiPricesError ? (
                    <p className="panel-footnote">Price changes could not be loaded.</p>
                  ) : mandiPriceChanges.length > 0 ? (
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Commodity</th>
                            <th>Market</th>
                            <th>Arrival date</th>
                            <th>Previous price</th>
                            <th>Current price</th>
                            <th>Change</th>
                            <th>Direction</th>
                          </tr>
                        </thead>
                        <tbody>
                          {mandiPriceChanges.map((item, index) => (
                            <tr key={`${item.state}-${item.market}-${item.commodity}-${item.current_observed_at}-${index}`}>
                              <td>{item.commodity ?? '—'}</td>
                              <td>{item.market ?? '—'}</td>
                              <td>{item.arrival_date ?? '—'}</td>
                              <td>{item.previous_modal_price == null ? '—' : `₹${Number(item.previous_modal_price).toLocaleString('en-IN')}`}</td>
                              <td>{item.current_modal_price == null ? '—' : `₹${Number(item.current_modal_price).toLocaleString('en-IN')}`}</td>
                              <td>{item.change_amount == null ? '—' : `${Number(item.change_amount) > 0 ? '+' : ''}₹${Number(item.change_amount).toLocaleString('en-IN')}`} {item.change_percent == null ? '' : `(${Number(item.change_percent).toFixed(2)}%)`}</td>
                              <td className={item.direction === 'INCREASE' ? 'warning-text' : 'success-text'}>{item.direction ?? '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="no-alerts">No price movements detected yet. The tracker will list changes when comparable observations show a different modal price.</p>
                  )}
                </div>
              </section>
            )}

            <section className="content-grid">
              <section className="panel quality-panel" id="quality">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">QUALITY METRICS</p>
                    <h3>Completeness overview</h3>
                  </div>
                  <span className="small-tag">01</span>
                </div>

                <div className="completeness-number">
                  <strong>{completeness.toFixed(1)}%</strong>
                  <span>completeness score</span>
                </div>

                <div
                  className="progress-track"
                  role="progressbar"
                  aria-label="Data completeness"
                  aria-valuenow={Math.min(100, Math.max(0, completeness))}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="progress-fill"
                    style={{
                      width: `${Math.min(100, Math.max(0, completeness))}%`,
                    }}
                  />
                </div>

                <div className="progress-labels">
                  <span>0%</span>
                  <span>100%</span>
                </div>

                <div className="record-stats">
                  <div>
                    <span className="field-label">RECORDS FETCHED</span>
                    <h3>{metrics.records_fetched ?? '—'}</h3>
                  </div>
                  <div>
                    <span className="field-label">SOURCE TOTAL</span>
                    <h3>{metrics.records_reported ?? '—'}</h3>
                  </div>
                </div>

                <div className="notice">
                  <span className="notice-marker" />
                  <p>
                    Fetched records may represent only part of the source
                    dataset when the API applies a record limit.
                  </p>
                </div>

                <div className="field-breakdown">
                  <h4>Missing values by field</h4>

                  {Object.keys(missingByField).length > 0 ? (
                    Object.entries(missingByField).map(([field, count]) => (
                      <div className="field-row" key={field}>
                        <span>{field}</span>
                        <strong>{count}</strong>
                      </div>
                    ))
                  ) : (
                    <p className="subtitle">
                      No field-level breakdown is available.
                    </p>
                  )}
                </div>
              </section>

              <section className="panel checks-panel">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">VALIDATION</p>
                    <h3>Health checks</h3>
                  </div>
                  <span className="small-tag">02</span>
                </div>

                <div className="check-row">
                  <div>
                    <span className="check-symbol success-text">✓</span>
                    <span>Schema validation</span>
                  </div>
                  <span className={`check-result ${schemaClass}`}>
                    {schemaValid === true
                      ? 'Passed'
                      : schemaValid === false
                        ? 'Failed'
                        : 'Unknown'}
                  </span>
                </div>

                <div className="check-row">
                  <div>
                    <span
                      className={`check-symbol ${
                        completeness >= 95 ? 'success-text' : 'warning-text'
                      }`}
                    >
                      {completeness >= 95 ? '✓' : '!'}
                    </span>
                    <span>Data completeness</span>
                  </div>
                  <span
                    className={`check-result ${
                      completeness >= 95 ? 'success-text' : 'warning-text'
                    }`}
                  >
                    {completeness >= 95 ? 'Good' : 'Needs review'}
                  </span>
                </div>

                <div className="check-row">
                  <div>
                    <span className={`check-symbol ${freshnessClass}`}>
                      {freshness === 'FRESH'
                        ? '✓'
                        : freshness === 'STALE'
                          ? '!'
                          : '?'}
                    </span>
                    <span>Source freshness</span>
                  </div>
                  <span className={`check-result ${freshnessClass}`}>
                    {freshness}
                  </span>
                </div>

                <p className="panel-footnote">
                  These checks describe the retrieved dataset and its source
                  metadata. A valid schema does not guarantee complete or
                  up-to-date data.
                </p>
              </section>
            </section>

            <section className="panel history-panel" id="changes">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">MONITORING INTELLIGENCE</p>
                  <h3>Change detection</h3>
                </div>
                <span className="small-tag">03</span>
              </div>

              {comparisonError ? (
                <p className="panel-footnote">{comparisonError}</p>
              ) : comparison ? (
                <>
                  <div className="comparison-meta">
                    <div>
                      <span className="field-label">PREVIOUS CHECK</span>
                      <p>{formatDate(comparison.previous_checked_at)}</p>
                    </div>
                    <div>
                      <span className="field-label">CURRENT CHECK</span>
                      <p>{formatDate(comparison.current_checked_at)}</p>
                    </div>
                  </div>

                  <style>{`
                    .record-change-summary {
                      display: grid;
                      grid-template-columns: repeat(3, minmax(0, 1fr));
                      gap: 12px;
                      margin: 16px 0;
                    }
                    .record-change-stat {
                      display: flex;
                      flex-direction: column;
                      gap: 8px;
                      padding: 16px;
                      border: 1px solid var(--border-color, rgba(220, 190, 220, 0.18));
                      background: rgba(255, 255, 255, 0.025);
                    }
                    .record-change-stat strong {
                      font-size: 1.8rem;
                      font-weight: 600;
                    }
                    .record-change-details {
                      margin-top: 20px;
                    }
                    .record-change-details h4 {
                      margin-bottom: 12px;
                    }
                    @media (max-width: 640px) {
                      .record-change-summary {
                        grid-template-columns: 1fr;
                      }
                    }
                  `}</style>
                  <div className="comparison-group">
                    <h4>Record-level changes</h4>
                    {comparison.record_changes ? (
                      <>
                        <div className="record-change-summary">
                          <div className="record-change-stat">
                            <span className="field-label">ADDED</span>
                            <strong>{comparison.record_changes.added_count ?? 0}</strong>
                          </div>
                          <div className="record-change-stat">
                            <span className="field-label">REMOVED</span>
                            <strong>{comparison.record_changes.removed_count ?? 0}</strong>
                          </div>
                          <div className="record-change-stat">
                            <span className="field-label">MODIFIED</span>
                            <strong>{comparison.record_changes.modified_count ?? 0}</strong>
                          </div>
                        </div>

                        <p className="panel-footnote">
                          Comparing {comparison.record_changes.records_previous ?? '—'} records in the previous snapshot
                          with {comparison.record_changes.records_current ?? '—'} in the current snapshot.
                        </p>

                        {comparison.record_changes.modified_records?.length > 0 && (
                          <div className="record-change-details">
                            <h4>Modified records</h4>
                            <div className="table-wrap" style={{ maxHeight: 360, overflowY: 'auto' }}>
                              <table>
                                <thead>
                                  <tr>
                                    <th>Record</th>
                                    <th>Field</th>
                                    <th>Previous value</th>
                                    <th>Current value</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {comparison.record_changes.modified_records
                                    .flatMap((record, recordIndex) => {
                                      const changedFields = record.changed_fields ?? {}
                                      return Object.entries(changedFields).map(([field, values], fieldIndex) => (
                                        <tr key={`${formatRecordIdentifier(record, selectedDataset)}-${field}-${recordIndex}-${fieldIndex}`}>
                                          <td>{formatRecordIdentifier(record, selectedDataset)}</td>
                                          <td>{field}</td>
                                          <td>{String(values?.previous ?? '—')}</td>
                                          <td>{String(values?.current ?? '—')}</td>
                                        </tr>
                                      ))
                                    })
                                    .slice(0, 10)}
                                </tbody>
                              </table>
                            </div>
                            {comparison.record_changes.modified_records.flatMap((record) =>
                              Object.keys(record.changed_fields ?? {})
                            ).length > 10 && (
                              <p className="panel-footnote">Showing the first 10 changed fields.</p>
                            )}
                          </div>
                        )}

                        {comparison.record_changes.added_records?.length > 0 && (
                          <div className="record-change-details">
                            <h4>Added records</h4>
                            <div className="table-wrap" style={{ maxHeight: 360, overflowY: 'auto' }}>
                              <table>
                                <thead>
                                  <tr>
                                    {changeRecordFields.map((field) => <th key={field.key}>{field.label}</th>)}
                                  </tr>
                                </thead>
                                <tbody>
                                  {comparison.record_changes.added_records.slice(0, 10).map((record, index) => (
                                    <tr key={`${formatRecordIdentifier(record, selectedDataset)}-${index}`}>
                                      {changeRecordFields.map((field) => (
                                        <td key={field.key}>{record[field.key] ?? '—'}</td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            {comparison.record_changes.added_records.length > 10 && (
                              <p className="panel-footnote">Showing 10 of {comparison.record_changes.added_records.length} added records.</p>
                            )}
                          </div>
                        )}

                        {comparison.record_changes.removed_records?.length > 0 && (
                          <div className="record-change-details">
                            <h4>Removed records</h4>
                            <div className="table-wrap" style={{ maxHeight: 360, overflowY: 'auto' }}>
                              <table>
                                <thead>
                                  <tr>
                                    {changeRecordFields.map((field) => <th key={field.key}>{field.label}</th>)}
                                  </tr>
                                </thead>
                                <tbody>
                                  {comparison.record_changes.removed_records.slice(0, 10).map((record, index) => (
                                    <tr key={`${formatRecordIdentifier(record, selectedDataset)}-${index}`}>
                                      {changeRecordFields.map((field) => (
                                        <td key={field.key}>{record[field.key] ?? '—'}</td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            {comparison.record_changes.removed_records.length > 10 && (
                              <p className="panel-footnote">Showing 10 of {comparison.record_changes.removed_records.length} removed records.</p>
                            )}
                          </div>
                        )}

                        {(comparison.record_changes.added_count ?? 0) === 0 &&
                          (comparison.record_changes.removed_count ?? 0) === 0 &&
                          (comparison.record_changes.modified_count ?? 0) === 0 && (
                            <p className="no-alerts">No record-level differences detected between these snapshots.</p>
                          )}
                      </>
                    ) : (
                      <p className="panel-footnote">
                        Record-level comparison is not available in this response. Refresh the dashboard and check the API endpoint.
                      </p>
                    )}
                  </div>

                  <div className="comparison-group">
                    <h4>Health metric changes</h4>
                    {comparison.changes?.length ? (
                      comparison.changes.map((change, index) => (
                        <div className="comparison-row" key={index}>
                          <span className="comparison-marker" />
                          <p>{change}</p>
                        </div>
                      ))
                    ) : (
                      <p className="no-alerts">No health metric changes reported.</p>
                    )}
                  </div>

                  <div className="comparison-group">
                    <h4>Alerts</h4>
                    {comparison.alerts?.length ? (
                      comparison.alerts.map((alert, index) => (
                        <div
                          className="comparison-row alert-row"
                          key={index}
                        >
                          <span className="comparison-marker" />
                          <p>
                            {typeof alert === 'string'
                              ? alert
                              : alert.message ?? JSON.stringify(alert)}
                          </p>
                        </div>
                      ))
                    ) : (
                      <p className="no-alerts">
                        No comparison alerts detected between these runs.
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <p className="panel-footnote">
                  Run monitoring at least twice to compare reports.
                </p>
              )}
            </section>

            <section className="panel history-panel" id="trends">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">QUALITY OVER TIME</p>
                  <h3>Historical trends</h3>
                </div>
                <span className="small-tag">{trends.length} CHECKS</span>
              </div>

              <p className="panel-footnote">
                Each point represents a saved monitoring report. These charts show
                changes in the retrieved data over time, not necessarily changes
                made by the publisher.
              </p>

              {trendsError ? (
                <p className="panel-footnote">{trendsError}</p>
              ) : trends.length === 0 ? (
                <p className="panel-footnote">
                  No trend history is available yet. Run the monitor to create reports.
                </p>
              ) : (
                <div className="trend-grid">
                  <style>{`
                    .trend-grid {
                      display: grid;
                      grid-template-columns: repeat(2, minmax(0, 1fr));
                      gap: 28px;
                      margin-top: 22px;
                    }
                    .trend-chart {
                      min-width: 0;
                      height: 270px;
                    }
                    .trend-chart h4 {
                      margin: 0 0 14px;
                      font-size: 0.95rem;
                      font-weight: 600;
                    }
                    .trend-empty {
                      min-height: 210px;
                      display: flex;
                      align-items: center;
                      color: var(--muted-text, #b7a9bd);
                      font-size: 0.9rem;
                    }
                    @media (max-width: 760px) {
                      .trend-grid { grid-template-columns: 1fr; }
                    }
                  `}</style>

                  <div className="trend-chart">
                    <h4>Completeness (%)</h4>
                    {trends.some((point) => point.completeness_percent != null) ? (
                      <ResponsiveContainer width="100%" height="88%">
                        <LineChart
                          data={trends}
                          margin={{ top: 8, right: 12, left: -14, bottom: 8 }}
                        >
                          <CartesianGrid
                            stroke="rgba(220, 190, 220, 0.14)"
                            strokeDasharray="3 3"
                          />
                          <XAxis
                            dataKey="checked_at"
                            tickFormatter={(value) =>
                              new Date(value).toLocaleDateString('en-IN', {
                                day: '2-digit',
                                month: 'short',
                              })
                            }
                            tick={{ fill: '#b7a9bd', fontSize: 11 }}
                            axisLine={{ stroke: 'rgba(220, 190, 220, 0.22)' }}
                            tickLine={false}
                            minTickGap={24}
                          />
                          <YAxis
                            domain={[0, 100]}
                            tick={{ fill: '#b7a9bd', fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                            tickFormatter={(value) => `${value}%`}
                          />
                          <Tooltip
                            labelFormatter={(value) => formatDate(value)}
                            formatter={(value) =>
                              value == null ? ['No data', 'Completeness'] : [`${Number(value).toFixed(2)}%`, 'Completeness']
                            }
                            contentStyle={{
                              background: '#241d2b',
                              border: '1px solid rgba(220, 190, 220, 0.22)',
                              borderRadius: 2,
                              color: '#f4eaf2',
                            }}
                          />
                          <Line
                            type="monotone"
                            dataKey="completeness_percent"
                            name="Completeness"
                            stroke="#e8a0b5"
                            strokeWidth={2}
                            dot={{ r: 3, fill: '#e8a0b5', strokeWidth: 0 }}
                            activeDot={{ r: 5 }}
                            connectNulls={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="trend-empty">
                        Completeness values are not available in the saved reports.
                      </div>
                    )}
                  </div>

                  <div className="trend-chart">
                    <h4>Missing field values</h4>
                    {trends.some((point) => point.missing_values != null) ? (
                      <ResponsiveContainer width="100%" height="88%">
                        <LineChart
                          data={trends}
                          margin={{ top: 8, right: 12, left: -14, bottom: 8 }}
                        >
                          <CartesianGrid
                            stroke="rgba(220, 190, 220, 0.14)"
                            strokeDasharray="3 3"
                          />
                          <XAxis
                            dataKey="checked_at"
                            tickFormatter={(value) =>
                              new Date(value).toLocaleDateString('en-IN', {
                                day: '2-digit',
                                month: 'short',
                              })
                            }
                            tick={{ fill: '#b7a9bd', fontSize: 11 }}
                            axisLine={{ stroke: 'rgba(220, 190, 220, 0.22)' }}
                            tickLine={false}
                            minTickGap={24}
                          />
                          <YAxis
                            allowDecimals={false}
                            tick={{ fill: '#b7a9bd', fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                          />
                          <Tooltip
                            labelFormatter={(value) => formatDate(value)}
                            formatter={(value) =>
                              value == null ? ['No data', 'Missing values'] : [value, 'Missing values']
                            }
                            contentStyle={{
                              background: '#241d2b',
                              border: '1px solid rgba(220, 190, 220, 0.22)',
                              borderRadius: 2,
                              color: '#f4eaf2',
                            }}
                          />
                          <Line
                            type="monotone"
                            dataKey="missing_values"
                            name="Missing values"
                            stroke="#d9b18c"
                            strokeWidth={2}
                            dot={{ r: 3, fill: '#d9b18c', strokeWidth: 0 }}
                            activeDot={{ r: 5 }}
                            connectNulls={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="trend-empty">
                        Missing-value counts are not available in the saved reports.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </section>

            <section className="panel history-panel" id="history">
              <details className="report-history-details">
                <summary className="report-history-summary">
                  <div>
                    <p className="eyebrow">RUN ARCHIVE</p>
                    <h3>Monitoring report history</h3>
                    <p className="panel-footnote">
                      Expand to review previous monitoring runs. Choose how many reports to display.
                    </p>
                  </div>
                  <span className="small-tag">{history.length} REPORTS</span>
                </summary>

                <div className="report-history-controls">
                  <label htmlFor="report-history-limit">Rows to display</label>
                  <select
                    id="report-history-limit"
                    value={reportHistoryLimit}
                    onChange={(event) => setReportHistoryLimit(Number(event.target.value))}
                  >
                    <option value={10}>10 rows</option>
                    <option value={25}>25 rows</option>
                    <option value={50}>50 rows</option>
                    <option value={100}>100 rows</option>
                  </select>
                  <span className="panel-footnote">
                    Showing {Math.min(reportHistoryLimit, history.length)} of {history.length} reports
                  </span>
                </div>

                <div className="table-wrap">
                  {history.length > 0 ? (
                    <table>
                      <thead>
                        <tr>
                          <th>Dataset</th>
                          <th>Checked at</th>
                          <th>Completeness</th>
                          <th>Schema</th>
                          <th>Freshness</th>
                        </tr>
                      </thead>
                      <tbody>
                        {history.slice(0, reportHistoryLimit).map((item, index) => {
                          const historicalReport = item.report ?? item
                          const historicalMetrics = historicalReport.health_metrics ?? {}

                          return (
                            <tr
                              key={item.filename ?? historicalReport.checked_at ?? index}
                            >
                              <td>{historicalReport.dataset ?? 'Unknown'}</td>
                              <td>{formatDate(historicalReport.checked_at)}</td>
                              <td>
                                {historicalMetrics.completeness_percent == null
                                  ? '—'
                                  : `${Number(historicalMetrics.completeness_percent).toFixed(1)}%`}
                              </td>
                              <td
                                className={`table-status ${
                                  historicalMetrics.schema_valid === true
                                    ? 'success-text'
                                    : historicalMetrics.schema_valid === false
                                      ? 'warning-text'
                                      : 'neutral-text'
                                }`}
                              >
                                {historicalMetrics.schema_valid === true
                                  ? 'Valid'
                                  : historicalMetrics.schema_valid === false
                                    ? 'Invalid'
                                    : 'Unknown'}
                              </td>
                              <td>{historicalMetrics.freshness_status ?? 'UNKNOWN'}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  ) : (
                    <p className="panel-footnote">No historical reports are available.</p>
                  )}
                </div>

                <p className="table-caption">
                  Showing the most recent monitoring reports available from the API.
                </p>
              </details>
            </section>

            <footer className="footer">
              <span>DataPulse India</span>
              <span>Public data quality monitoring</span>
            </footer>
          </>
        )}
      </main>
    </div>
  )
}

export default App
