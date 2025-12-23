import React, { useState, useEffect, useMemo } from 'react';
import { ExternalLink, Search, Filter, Database, Check, Clock } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

function App() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const itemsPerPage = 50;

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/data/videos.json');
        if (!response.ok) throw new Error('No data found');
        const data = await response.json();
        setVideos(data);
      } catch (e) {
        console.error("Failed to fetch videos.json", e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const filteredVideos = useMemo(() => {
    return videos.filter(v =>
      v.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.id.includes(searchTerm)
    );
  }, [videos, searchTerm]);

  const totalPages = Math.ceil(filteredVideos.length / itemsPerPage);
  const currentVideos = filteredVideos.slice((page - 1) * itemsPerPage, page * itemsPerPage);

  // Get all unique playlist titles from data
  const playlistHeaders = useMemo(() => {
    const titles = new Set();
    videos.forEach(v => Object.keys(v.playlists).forEach(t => titles.add(t)));
    return Array.from(titles).sort();
  }, [videos]);

  if (loading) return <div style={{ color: 'white', padding: '2rem' }}>Loading HCL Content Matrix...</div>;

  return (
    <div className="dashboard-container" style={{ maxWidth: '100%', padding: '1rem' }}>
      <header className="header">
        <div>
          <h1>HCL CONTENT MATRIX</h1>
          <p style={{ color: 'rgba(255,255,255,0.5)' }}>Video-to-Playlist Cross-Reference System</p>
        </div>

        <div className="stats-bar">
          <div className="stat-card">
            <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>TOTAL VIDEOS</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{videos.length}</div>
          </div>
          <div className="stat-card">
            <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>PLAYLISTS</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{playlistHeaders.length}</div>
          </div>
        </div>
      </header>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '300px' }}>
          <Search style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', opacity: 0.4 }} size={18} />
          <input
            type="text"
            placeholder="Search by title or video ID..."
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
            style={{
              width: '100%',
              padding: '0.75rem 1rem 0.75rem 2.5rem',
              borderRadius: '0.75rem',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: 'white',
              fontSize: '1rem'
            }}
          />
        </div>
        <div className="stat-card" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.5rem 1rem' }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</button>
          <span>Page {page} of {totalPages || 1}</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Next</button>
        </div>
      </div>

      <div style={{ overflowX: 'auto', background: 'rgba(255,255,255,0.02)', borderRadius: '1rem', border: '1px solid rgba(255,255,255,0.05)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ background: 'rgba(255,255,255,0.05)' }}>
              <th style={{ padding: '1rem' }}>Title</th>
              <th style={{ padding: '1rem' }}>Published</th>
              {playlistHeaders.map(h => (
                <th key={h} style={{ padding: '1rem', fontSize: '0.65rem', maxWidth: '80px', textAlign: 'center' }}>
                  <div style={{ transform: 'rotate(-45deg)', whiteSpace: 'nowrap', width: '20px' }}>{h}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {currentVideos.map(v => (
              <tr key={v.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <td style={{ padding: '0.75rem 1rem', fontWeight: 500 }}>
                  <a href={`https://www.youtube.com/watch?v=${v.id}`} target="_blank" rel="noreferrer" style={{ color: '#fbbf24', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {v.title} <ExternalLink size={12} />
                  </a>
                </td>
                <td style={{ padding: '0.75rem 1rem', opacity: 0.6, whiteSpace: 'nowrap' }}>
                  {new Date(v.publishedAt).toLocaleDateString()}
                </td>
                {playlistHeaders.map(h => (
                  <td key={h} style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                    {v.playlists[h] ? (
                      <div style={{ width: '16px', height: '16px', background: '#f59e0b', borderRadius: '4px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyCenter: 'center' }}>
                        <Check size={12} color="black" strokeWidth={4} />
                      </div>
                    ) : (
                      <div style={{ width: '16px', height: '16px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '4px', margin: '0 auto' }} />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ textAlign: 'center', marginTop: '2rem', opacity: 0.3, fontSize: '0.75rem' }}>
        Found {filteredVideos.length} matching content items.
      </div>
    </div>
  );
}

export default App;
