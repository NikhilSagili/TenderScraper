import React, { useState } from 'react';
import axios from 'axios';
import Papa from 'papaparse';
import './App.css';

function App() {
    const [url, setUrl] = useState('https://bidplus.gem.gov.in/advance-search');
    const [startDate, setStartDate] = useState(new Date(new Date().setDate(new Date().getDate() - 2)).toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
    const [bids, setBids] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleScrape = async () => {
        setLoading(true);
        setError('');
        setBids([]);

        try {
            // Use the Render backend URL - replace 'your-render-app-url' with your actual Render URL
            const BACKEND_URL = 'https://your-render-app.onrender.com';
            const response = await axios.post(`${BACKEND_URL}/scrape`, {
                url,
                startDate,
                endDate,
            });
            setBids(response.data);
        } catch (err) {
            setError('Failed to scrape data. Make sure the backend server is running.');
            console.error(err);
        }
        setLoading(false);
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
                <div className="controls">
                    <div className="input-group">
                        <label htmlFor="url">Target URL</label>
                        <input
                            type="text"
                            id="url"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                        />
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
                    <button onClick={handleScrape} disabled={loading}>
                        {loading ? 'Scraping...' : 'Scrape Bids'}
                    </button>
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

