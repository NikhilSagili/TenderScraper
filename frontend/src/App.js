import React, { useState } from 'react';
import axios from 'axios';
import Papa from 'papaparse';
import './App.css';

function App() {
    const [url, setUrl] = useState('https://bidplus.gem.gov.in/advance-search');
    const [startDate, setStartDate] = useState(new Date(new Date().setDate(new Date().getDate() - 2)).toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
    const [state, setState] = useState('ANDHRA PRADESH'); // Default state
    const [bids, setBids] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [healthStatus, setHealthStatus] = useState('');
    
    // Backend URL - update this to your Render URL
    const BACKEND_URL = process.env.REACT_APP_API_URL || 'https://gem-scraper-backend.onrender.com';

    const handleScrape = async () => {
        setLoading(true);
        setError('');
        setBids([]);

        try {
            const response = await axios.post(`${BACKEND_URL}/scrape`, {
                url,
                startDate,
                endDate,
                state, // Add selected state to the request
            }, {
                timeout: 900000, // 5 minutes timeout
                headers: {
                    'Content-Type': 'application/json'
                },
                onUploadProgress: (progressEvent) => {
                    // Optional: Add progress tracking if needed
                    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    console.log(`Upload Progress: ${progress}%`);
                },
                onDownloadProgress: (progressEvent) => {
                    // Optional: Add progress tracking if needed
                    const progress = progressEvent.loaded ? Math.round((progressEvent.loaded * 100) / progressEvent.total) : 0;
                    console.log(`Download Progress: ${progress}%`);
                }
            });
            
            if (response.data.error) {
                throw new Error(response.data.details || response.data.error);
            }
            
            // The backend now returns data in response.data.data
            setBids(response.data.data || []);
            
            // Show a success message if no bids were found
            if (response.data.message && response.data.message.includes('No bids')) {
                setError(response.data.message);
            }
        } catch (err) {
            let errorMessage = 'Failed to scrape data. ';
            
            if (err.code === 'ECONNABORTED') {
                errorMessage += 'The request took too long. The server might be processing a large amount of data.';
            } else if (err.response) {
                // Server responded with an error status code
                errorMessage += `Server responded with status ${err.response.status}: ${err.response.data?.error || 'Unknown error'}`;
            } else if (err.request) {
                // Request was made but no response received
                errorMessage += 'No response received from the server. The backend might be down or unreachable.';
            } else {
                // Something else caused the error
                errorMessage += err.message || 'An unknown error occurred.';
            }
            
            setError(errorMessage);
            console.error('Scraping error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleHealthCheck = async () => {
        try {
            const response = await axios.get(`${BACKEND_URL}/health`);
            setHealthStatus({
                ...response.data,
                timestamp: new Date().toISOString()
            });
        } catch (err) {
            console.error('Health check failed:', err);
            setHealthStatus({
                status: 'error',
                error: 'Backend server is not responding',
                timestamp: new Date().toISOString()
            });
        }
    };

    const handleDownload = () => {
        const csv = Papa.unparse(bids);
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.setAttribute('download', 'gem_bids.csv');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <div className="App">
            <header className="App-header">
                <h1>GeM Bid Scraper</h1>
            </header>
            <main>
                <div className="container">
                    <div className="input-group">
                        <label htmlFor="url">GeM Advanced Search URL</label>
                        <input
                            type="text"
                            id="url"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                        />
                    </div>
                    <div className="form-row">
                        <div className="input-group">
                            <label htmlFor="state">State</label>
                            <select id="state" value={state} onChange={(e) => setState(e.target.value)}>
                                <option value="ANDHRA PRADESH">Andhra Pradesh</option>
                                <option value="TELANGANA">Telangana</option>
                            </select>
                        </div>
                        <div className="input-group">
                            <label htmlFor="startDate">Start Date</label>
                            <input
                                type="date"
                                id="startDate"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                            />
                        </div>
                        <div className="input-group">
                            <label htmlFor="endDate">End Date</label>
                            <input
                                type="date"
                                id="endDate"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="button-group">
                        <button onClick={handleScrape} disabled={loading}>
                            {loading ? 'Scraping...' : 'Scrape Bids'}
                        </button>
                        <button onClick={handleHealthCheck} className="health-btn">
                            Check Backend Status
                        </button>
                    </div>
                    {healthStatus && (
                        <div className={`health-status ${healthStatus.status === 'healthy' ? 'healthy' : 'error'}`}>
                            {healthStatus.status === 'healthy' ? '✅ Backend is healthy' : '❌ Backend error'}
                            {healthStatus.timestamp && ` (${new Date(healthStatus.timestamp).toLocaleString()})`}
                        </div>
                    )}
                </div>

                {error && <p className="error">{error}</p>}

                {bids.length > 0 && (
                    <div className="results">
                        <h2>Scraped Bids</h2>
                        <button onClick={handleDownload} className="download-btn">
                            Download CSV
                        </button>
                        <table>
                            <thead>
                                <tr>
                                    {Object.keys(bids[0]).map((key) => (
                                        <th key={key}>{key}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {bids.map((bid, index) => (
                                    <tr key={index}>
                                        {Object.values(bid).map((value, i) => (
                                            <td key={i}>{value}</td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </main>
        </div>
    );
}

export default App;

