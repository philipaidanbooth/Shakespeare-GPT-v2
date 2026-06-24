import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';

const backendUrl = 'https://shakespeare-gpt-v2-production-3c45.up.railway.app';

interface EvalRun {
  id: number;
  run_at: string;
  total: number;
  errors: number;
  format_pct: number;
  citation_pct: number;
  judge_avg: number;
}

interface PlayRow {
  play: string;
  total: number;
  judge_avg: number;
  citation_pct: number;
  format_pct: number;
}

interface TypeRow {
  type: string;
  total: number;
  judge_avg: number;
  citation_pct: number;
  format_pct: number;
}

interface EvalResults {
  run: EvalRun | null;
  by_play: PlayRow[];
  by_type: TypeRow[];
}

function pct(val: number) {
  return `${Math.round(val * 100)}%`;
}

function score(val: number) {
  return val.toFixed(2);
}

function ScoreCard({ label, value, subtitle }: { label: string; value: string; subtitle: string }) {
  return (
    <div style={{
      background: 'linear-gradient(135deg, #FEFCF8 0%, #F7F3E8 100%)',
      border: '1px solid #E2E8F0',
      borderRadius: '12px',
      padding: '1.5rem',
      textAlign: 'center',
      flex: 1,
      minWidth: '140px',
    }}>
      <div style={{ fontSize: '2rem', fontWeight: 700, color: '#6B46C1', fontFamily: 'Playfair Display, serif' }}>
        {value}
      </div>
      <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#1A202C', marginTop: '0.25rem' }}>
        {label}
      </div>
      <div style={{ fontSize: '0.75rem', color: '#718096', marginTop: '0.25rem' }}>
        {subtitle}
      </div>
    </div>
  );
}

export default function EvalsPage() {
  const [data, setData] = useState<EvalResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${backendUrl}/eval-results`)
      .then(r => r.json())
      .then(setData)
      .catch(() => setError('Could not load eval results.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Head>
        <title>Shakespeare GPT — Eval Results</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet" />
      </Head>

      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #F5F1E8 0%, #E8E0D0 100%)',
        fontFamily: 'Inter, sans-serif',
        color: '#2D3748',
      }}>
        {/* Header */}
        <div style={{
          background: 'linear-gradient(135deg, #1A202C 0%, #2D3748 100%)',
          padding: '1.5rem 2rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontFamily: 'Playfair Display, serif', fontSize: '1.5rem', color: '#F7F3E8', fontWeight: 700 }}>
              Shakespeare GPT
            </div>
            <div style={{ fontSize: '0.8rem', color: '#A0AEC0', marginTop: '0.1rem' }}>
              Eval Results
            </div>
          </div>
          <Link href="/" style={{
            color: '#A0AEC0',
            textDecoration: 'none',
            fontSize: '0.85rem',
            border: '1px solid #4A5568',
            padding: '0.4rem 0.9rem',
            borderRadius: '6px',
            transition: 'all 0.2s',
          }}>
            ← Back to App
          </Link>
        </div>

        <div style={{ maxWidth: '860px', margin: '0 auto', padding: '2rem 1.5rem' }}>

          {loading && (
            <div style={{ textAlign: 'center', color: '#718096', padding: '4rem 0' }}>
              Loading eval results…
            </div>
          )}

          {error && (
            <div style={{ textAlign: 'center', color: '#E53E3E', padding: '4rem 0' }}>{error}</div>
          )}

          {data && !data.run && (
            <div style={{ textAlign: 'center', color: '#718096', padding: '4rem 0' }}>
              No eval runs yet. Run:<br />
              <code style={{ background: '#EDF2F7', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.85rem' }}>
                venv/bin/python evals/run_eval.py --url &lt;backend&gt; --save-to-db
              </code>
            </div>
          )}

          {data && data.run && (
            <>
              {/* Run metadata */}
              <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontFamily: 'Playfair Display, serif', fontSize: '1.8rem', fontWeight: 700, color: '#1A202C', margin: 0 }}>
                  Evaluation Results
                </h1>
                <p style={{ color: '#718096', fontSize: '0.85rem', marginTop: '0.4rem' }}>
                  Last run: {new Date(data.run.run_at).toLocaleString()} &nbsp;·&nbsp;
                  {data.run.total - data.run.errors}/{data.run.total} questions answered &nbsp;·&nbsp;
                  {data.run.errors} errors
                </p>
              </div>

              {/* Score cards */}
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '2.5rem' }}>
                <ScoreCard
                  label="Judge Score"
                  value={`${score(data.run.judge_avg)} / 5`}
                  subtitle="LLM-graded answer quality"
                />
                <ScoreCard
                  label="Citation Accuracy"
                  value={pct(data.run.citation_pct)}
                  subtitle="Act & scene matches source"
                />
                <ScoreCard
                  label="Format Compliance"
                  value={pct(data.run.format_pct)}
                  subtitle="All 4 sections present"
                />
              </div>

              {/* By play */}
              <div style={{ marginBottom: '2.5rem' }}>
                <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: '1.2rem', fontWeight: 600, color: '#1A202C', marginBottom: '0.75rem' }}>
                  By Play
                </h2>
                <div style={{ background: '#FEFCF8', border: '1px solid #E2E8F0', borderRadius: '10px', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                    <thead>
                      <tr style={{ background: 'linear-gradient(135deg, #6B46C1 0%, #553C9A 100%)', color: 'white' }}>
                        <th style={{ textAlign: 'left', padding: '0.75rem 1rem', fontWeight: 600 }}>Play</th>
                        <th style={{ textAlign: 'center', padding: '0.75rem 1rem', fontWeight: 600 }}>Qs</th>
                        <th style={{ textAlign: 'center', padding: '0.75rem 1rem', fontWeight: 600 }}>Judge Avg</th>
                        <th style={{ textAlign: 'center', padding: '0.75rem 1rem', fontWeight: 600 }}>Citation</th>
                        <th style={{ textAlign: 'center', padding: '0.75rem 1rem', fontWeight: 600 }}>Format</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.by_play.map((row, i) => (
                        <tr key={row.play} style={{ borderTop: '1px solid #E2E8F0', background: i % 2 === 0 ? '#FEFCF8' : '#F7F3E8' }}>
                          <td style={{ padding: '0.65rem 1rem', fontStyle: 'italic', color: '#1A202C' }}>{row.play}</td>
                          <td style={{ padding: '0.65rem 1rem', textAlign: 'center', color: '#718096' }}>{row.total}</td>
                          <td style={{ padding: '0.65rem 1rem', textAlign: 'center', fontWeight: 600, color: '#6B46C1' }}>{score(row.judge_avg)}</td>
                          <td style={{ padding: '0.65rem 1rem', textAlign: 'center', color: '#2D3748' }}>{pct(row.citation_pct)}</td>
                          <td style={{ padding: '0.65rem 1rem', textAlign: 'center', color: '#2D3748' }}>{pct(row.format_pct)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* By type */}
              <div style={{ marginBottom: '2rem' }}>
                <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: '1.2rem', fontWeight: 600, color: '#1A202C', marginBottom: '0.75rem' }}>
                  By Question Type
                </h2>
                <div style={{ background: '#FEFCF8', border: '1px solid #E2E8F0', borderRadius: '10px', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                    <thead>
                      <tr style={{ background: 'linear-gradient(135deg, #6B46C1 0%, #553C9A 100%)', color: 'white' }}>
                        <th style={{ textAlign: 'left', padding: '0.75rem 1rem', fontWeight: 600 }}>Type</th>
                        <th style={{ textAlign: 'center', padding: '0.75rem 1rem', fontWeight: 600 }}>Qs</th>
                        <th style={{ textAlign: 'center', padding: '0.75rem 1rem', fontWeight: 600 }}>Judge Avg</th>
                        <th style={{ textAlign: 'center', padding: '0.75rem 1rem', fontWeight: 600 }}>Citation</th>
                        <th style={{ textAlign: 'center', padding: '0.75rem 1rem', fontWeight: 600 }}>Format</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.by_type.map((row, i) => (
                        <tr key={row.type} style={{ borderTop: '1px solid #E2E8F0', background: i % 2 === 0 ? '#FEFCF8' : '#F7F3E8' }}>
                          <td style={{ padding: '0.65rem 1rem', textTransform: 'capitalize', color: '#1A202C' }}>{row.type}</td>
                          <td style={{ padding: '0.65rem 1rem', textAlign: 'center', color: '#718096' }}>{row.total}</td>
                          <td style={{ padding: '0.65rem 1rem', textAlign: 'center', fontWeight: 600, color: '#6B46C1' }}>{score(row.judge_avg)}</td>
                          <td style={{ padding: '0.65rem 1rem', textAlign: 'center', color: '#2D3748' }}>{pct(row.citation_pct)}</td>
                          <td style={{ padding: '0.65rem 1rem', textAlign: 'center', color: '#2D3748' }}>{pct(row.format_pct)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Metric definitions */}
              <div style={{ background: '#FEFCF8', border: '1px solid #E2E8F0', borderRadius: '10px', padding: '1.25rem 1.5rem', fontSize: '0.8rem', color: '#718096' }}>
                <strong style={{ color: '#4A5568' }}>About these metrics</strong>
                <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem', lineHeight: 1.7 }}>
                  <li><strong>Judge Score (1–5)</strong> — Claude Haiku grades each answer against a SparkNotes reference. 5 = excellent, 1 = wrong or fabricated.</li>
                  <li><strong>Citation Accuracy</strong> — The act and scene cited in the answer matches one of the retrieved source chunks.</li>
                  <li><strong>Format Compliance</strong> — All four required sections (Context, Specific Moment, Quote, Analysis) are present.</li>
                </ul>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
