// front/frontend/src/App.js

import React, { useState, useEffect, useCallback } from 'react';
// ייבוא האייקונים מ-lucide-react
import { Activity, Server, Network, AlertTriangle, Box, Zap, Clock, TrendingUp } from 'lucide-react';

// ======================================================
// 1. התיקון הקריטי: קביעת כתובות API ו-WS בקיבוע
// ======================================================

const API_BASE_HOST_PORT = 'localhost:8000';
const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';

// קביעת כתובת בסיס ל-API (http://localhost:8000)
const API_BASE_URL = `http://${API_BASE_HOST_PORT}`; 
// קביעת כתובת WebSocket (ws://localhost:8000/ws)
const WS_URL = `${wsProtocol}://${API_BASE_HOST_PORT}/ws`;

// ======================================================
// 2. רכיבי עזר (ללא שינוי מהותי, הועברו למעלה)
// ======================================================

// Stat Card Component
const StatCard = ({ icon, label, value, color }) => (
    // ... (קוד StatCard כפי שהיה)
    <div className="transition-all hover-scale" style={{
        background: 'rgba(30, 41, 59, 0.5)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(148, 163, 184, 0.1)',
        borderRadius: '12px',
        padding: '16px',
        cursor: 'pointer'
    }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{
                width: '40px',
                height: '40px',
                background: color,
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
            }}>
                {icon}
            </div>
            <TrendingUp size={16} style={{ color: '#10b981' }} />
        </div>
        <div style={{ fontSize: '28px', fontWeight: 'bold', marginBottom: '4px' }}>{value}</div>
        <div style={{ fontSize: '12px', color: '#94a3b8' }}>{label}</div>
    </div>
);

// Topology View
const TopologyView = ({ data }) => (
    // ... (קוד TopologyView כפי שהיה)
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px' }}>
        <div style={{
            background: 'rgba(30, 41, 59, 0.5)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(148, 163, 184, 0.1)',
            borderRadius: '12px',
            padding: '24px'
        }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Network size={20} style={{ color: '#22d3ee' }} />
                Network Topology
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {data.nodes.slice(0, 10).map((node, i) => (
                    <div key={i} className="transition-all" style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        padding: '12px',
                        background: 'rgba(30, 41, 59, 0.5)',
                        borderRadius: '8px',
                        cursor: 'pointer'
                    }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(30, 41, 59, 0.8)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(30, 41, 59, 0.5)'}>
                        <div className="animate-pulse" style={{
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            background: node.status === 'running' ? '#10b981' : '#6b7280'
                        }}></div>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '2px' }}>{node.label}</div>
                            <div style={{ fontSize: '12px', color: '#94a3b8' }}>{node.ip}</div>
                        </div>
                        <div style={{
                            fontSize: '11px',
                            padding: '4px 8px',
                            background: 'rgba(6, 182, 212, 0.2)',
                            color: '#22d3ee',
                            borderRadius: '4px'
                        }}>
                            {node.classification || 'service'}
                        </div>
                    </div>
                ))}
            </div>
        </div>

        <div style={{
            background: 'rgba(30, 41, 59, 0.5)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(148, 163, 184, 0.1)',
            borderRadius: '12px',
            padding: '24px'
        }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={20} style={{ color: '#a855f7' }} />
                Active Flows
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {data.edges.slice(0, 10).map((edge, i) => (
                    <div key={i} className="transition-all" style={{
                        padding: '12px',
                        background: 'rgba(30, 41, 59, 0.5)',
                        borderRadius: '8px'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '13px' }}>
                            <span style={{ color: '#e2e8f0' }}>{edge.source}</span>
                            <span style={{ color: '#64748b' }}>→</span>
                            <span style={{ color: '#e2e8f0' }}>{edge.target}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{ flex: 1, height: '6px', background: '#334155', borderRadius: '3px', overflow: 'hidden' }}>
                                <div className="animate-pulse" style={{
                                    height: '100%',
                                    width: '60%',
                                    background: 'linear-gradient(90deg, #06b6d4, #3b82f6)',
                                    borderRadius: '3px'
                                }}></div>
                            </div>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>{Math.round(edge.bytes / 1024)}KB</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    </div>
);

// Connections View
const ConnectionsView = ({ connections }) => (
    // ... (קוד ConnectionsView כפי שהיה)
    <div style={{
        background: 'rgba(30, 41, 59, 0.5)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(148, 163, 184, 0.1)',
        borderRadius: '12px',
        overflow: 'hidden'
    }}>
        <div style={{ padding: '24px', borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={20} style={{ color: '#22d3ee' }} />
                Active Connections
            </h3>
        </div>
        <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead style={{ background: 'rgba(30, 41, 59, 0.5)' }}>
                    <tr>
                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '500', color: '#94a3b8' }}>Source</th>
                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '500', color: '#94a3b8' }}>Destination</th>
                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '500', color: '#94a3b8' }}>Port</th>
                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '500', color: '#94a3b8' }}>State</th>
                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '500', color: '#94a3b8' }}>Data</th>
                    </tr>
                </thead>
                <tbody>
                    {connections.slice(0, 20).map((conn, i) => (
                        <tr key={i} className="transition-all" style={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}
                            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(30, 41, 59, 0.3)'}
                            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                            <td style={{ padding: '16px 24px', fontSize: '14px' }}>{conn.src_ip}:{conn.src_port}</td>
                            <td style={{ padding: '16px 24px', fontSize: '14px' }}>{conn.dst_ip}:{conn.dst_port}</td>
                            <td style={{ padding: '16px 24px', fontSize: '14px' }}>{conn.dst_port}</td>
                            <td style={{ padding: '16px 24px' }}>
                                <span style={{
                                    fontSize: '12px',
                                    fontWeight: '500',
                                    color: conn.state === 'ESTABLISHED' ? '#10b981' : '#94a3b8'
                                }}>
                                    {conn.state}
                                </span>
                            </td>
                            <td style={{ padding: '16px 24px', fontSize: '14px', color: '#94a3b8' }}>
                                ↑{Math.round(conn.bytes_sent / 1024)}KB ↓{Math.round(conn.bytes_recv / 1024)}KB
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    </div>
);

// Containers View
const ContainersView = ({ containers }) => (
    // ... (קוד ContainersView כפי שהיה)
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        {containers.map((container, i) => (
            <div key={i} className="transition-all hover-scale" style={{
                background: 'rgba(30, 41, 59, 0.5)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(148, 163, 184, 0.1)',
                borderRadius: '12px',
                padding: '20px',
                cursor: 'pointer'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{
                            width: '40px',
                            height: '40px',
                            background: 'linear-gradient(135deg, #a855f7 0%, #ec4899 100%)',
                            borderRadius: '8px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <Box size={20} />
                        </div>
                        <div>
                            <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '2px' }}>{container.name}</div>
                            <div style={{ fontSize: '11px', color: '#94a3b8' }}>{container.image}</div>
                        </div>
                    </div>
                    <div className="animate-pulse" style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        background: container.status === 'running' ? '#10b981' : '#6b7280'
                    }}></div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                        <span style={{ color: '#94a3b8' }}>IP</span>
                        <span style={{ color: '#e2e8f0' }}>{container.ip_address}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                        <span style={{ color: '#94a3b8' }}>Networks</span>
                        <span style={{ color: '#e2e8f0' }}>{container.networks.join(', ')}</span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '8px' }}>
                        {container.ports.map((port, j) => (
                            <span key={j} style={{
                                fontSize: '11px',
                                padding: '2px 8px',
                                background: 'rgba(6, 182, 212, 0.2)',
                                color: '#22d3ee',
                                borderRadius: '4px'
                            }}>
                                {port}
                            </span>
                        ))}
                    </div>
                </div>
            </div>
        ))}
    </div>
);

// Ports View
const PortsView = ({ ports }) => (
    // ... (קוד PortsView כפי שהיה)
    <div style={{
        background: 'rgba(30, 41, 59, 0.5)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(148, 163, 184, 0.1)',
        borderRadius: '12px',
        padding: '24px'
    }}>
        <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Server size={20} style={{ color: '#f59e0b' }} />
            Open Ports
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
            {ports.map((port, i) => (
                <div key={i} className="transition-all hover-scale" style={{
                    padding: '16px',
                    background: 'rgba(30, 41, 59, 0.5)',
                    borderRadius: '8px',
                    cursor: 'pointer'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#f59e0b' }}>{port.port}</span>
                        <div className="animate-pulse" style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: '#10b981'
                        }}></div>
                    </div>
                    <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
                        {port.container || 'System'}
                    </div>
                    <div style={{ fontSize: '11px', color: '#10b981' }}>Listening</div>
                </div>
            ))}
        </div>
    </div>
);

// Anomalies View
const AnomaliesView = ({ anomalies }) => (
    // ... (קוד AnomaliesView כפי שהיה)
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {anomalies.length === 0 ? (
            <div style={{
                background: 'rgba(30, 41, 59, 0.5)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(148, 163, 184, 0.1)',
                borderRadius: '12px',
                padding: '48px',
                textAlign: 'center'
            }}>
                <div style={{
                    width: '64px',
                    height: '64px',
                    background: 'rgba(16, 185, 129, 0.2)',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 16px'
                }}>
                    <Activity size={32} style={{ color: '#10b981' }} />
                </div>
                <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>All Clear!</h3>
                <p style={{ fontSize: '14px', color: '#94a3b8' }}>No anomalies detected in your network</p>
            </div>
        ) : (
            anomalies.map((anomaly, i) => (
                <div key={i} className="transition-all hover-scale" style={{
                    background: 'rgba(30, 41, 59, 0.5)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(148, 163, 184, 0.1)',
                    borderRadius: '12px',
                    padding: '24px'
                }}>
                    <div style={{ display: 'flex', gap: '16px' }}>
                        <div style={{
                            width: '48px',
                            height: '48px',
                            background: anomaly.severity === 'CRITICAL'
                                ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
                                : 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)',
                            borderRadius: '8px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0
                        }}>
                            <AlertTriangle size={24} />
                        </div>
                        <div style={{ flex: 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                <span style={{
                                    fontSize: '11px',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    fontWeight: '500',
                                    background: anomaly.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(234, 179, 8, 0.2)',
                                    color: anomaly.severity === 'CRITICAL' ? '#ef4444' : '#eab308'
                                }}>
                                    {anomaly.severity}
                                </span>
                                <span style={{ fontSize: '12px', color: '#94a3b8' }}>{anomaly.type}</span>
                            </div>
                            <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '4px' }}>{anomaly.message}</div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#94a3b8' }}>
                                <Clock size={12} />
                                {new Date(anomaly.timestamp).toLocaleString()}
                            </div>
                            {anomaly.details && (
                                <div style={{
                                    marginTop: '12px',
                                    padding: '12px',
                                    background: 'rgba(30, 41, 59, 0.5)',
                                    borderRadius: '6px',
                                    fontSize: '11px',
                                    color: '#94a3b8',
                                    fontFamily: 'monospace',
                                    whiteSpace: 'pre-wrap'
                                }}>
                                    {JSON.stringify(anomaly.details, null, 2)}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            ))
        )}
    </div>
);


// ======================================================
// 3. רכיב ראשי (NetworkDashboard)
// ======================================================
const NetworkDashboard = () => {
    // Hooks חייבים להיות בראש הפונקציה
    const [activeView, setActiveView] = useState('topology');
    const [data, setData] = useState({
        topology: { nodes: [], edges: [] },
        connections: [],
        containers: [],
        ports: [],
        anomalies: [],
        stats: {}
    });
    const [isConnected, setIsConnected] = useState(false);

    // פונקציית משיכת נתונים מרוכזת (משתמשת ב-useCallback כדי למנוע יצירה מחדש)
    const fetchAllData = useCallback(async () => {
        try {
            // ה-Promise.all מבצע את כל הקריאות במקביל
            const [topology, connections, containers, ports, anomalies, stats] = await Promise.all([
                fetch(`${API_BASE_URL}/api/topology`).then(r => r.json()),
                fetch(`${API_BASE_URL}/api/connections`).then(r => r.json()),
                fetch(`${API_BASE_URL}/api/containers`).then(r => r.json()),
                fetch(`${API_BASE_URL}/api/ports`).then(r => r.json()),
                fetch(`${API_BASE_URL}/api/anomalies`).then(r => r.json()),
                fetch(`${API_BASE_URL}/api/stats`).then(r => r.json()),
            ]);

            // מעדכן את ה-State של הנתונים
            setData({
                topology,
                connections: connections.connections || [],
                containers: containers.containers || [],
                ports: ports.ports || [],
                anomalies: anomalies.anomalies || [],
                stats: stats
            });
            console.log("Data fetched successfully.");
        } catch (error) {
            console.error('Error fetching data:', error);
            // אם יש שגיאת CORS או שרת, זה יופיע כאן
        }
    }, []); // מערך תלויות ריק כי אנו משתמשים במשתנים גלובליים (API_BASE_URL)

    // WebSocket connection
    useEffect(() => {
        const ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            setIsConnected(true);
            console.log('Connected to master');
            // משיכה ראשונית של נתונים מיד לאחר החיבור
            fetchAllData(); 
        };

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            // מטפלים בסוגי ההודעות מה-Backend
            if (message.type === 'snapshot_update' || message.type === 'initial_snapshot') {
                fetchAllData();
            }
        };

        ws.onclose = () => {
            setIsConnected(false);
            console.log('WebSocket Disconnected');
        };
        ws.onerror = (error) => {
            console.error('WebSocket Error:', error);
            // נשאר setIsConnected(false) לאחר שגיאה
        };

        return () => ws.close();
    }, [fetchAllData]); // תלוי ב-fetchAllData

    // טיימר רגיל לשליפת נתונים בנוסף ל-WebSocket (למקרה שה-WS נכשל)
    useEffect(() => {
        // משיכה ראשונית של נתונים בטעינת הרכיב
        fetchAllData(); 
        const interval = setInterval(fetchAllData, 5000); 
        return () => clearInterval(interval);
    }, [fetchAllData]);


    return (
        <>
            {/* ... קוד ה-CSS Inline ... */}
            <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }
        
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          overflow-x: hidden;
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        .animate-pulse {
          animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        
        .hover-scale:hover {
          transform: translateY(-2px);
        }
        
        .transition-all {
          transition: all 0.3s ease;
        }
      `}</style>

            <div style={{
                minHeight: '100vh',
                background: 'linear-gradient(135deg, #0a0e1a 0%, #1e293b 100%)',
                color: '#fff'
            }}>
                {/* Header */}
                <div style={{
                    background: 'rgba(15, 23, 42, 0.8)',
                    backdropFilter: 'blur(10px)',
                    borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
                    position: 'sticky',
                    top: 0,
                    zIndex: 50
                }}>
                    <div style={{
                        maxWidth: '1600px',
                        margin: '0 auto',
                        padding: '16px 24px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div style={{
                                width: '40px',
                                height: '40px',
                                background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
                                borderRadius: '8px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}>
                                <Network size={24} />
                            </div>
                            <div>
                                <h1 style={{
                                    fontSize: '20px',
                                    fontWeight: 'bold',
                                    background: 'linear-gradient(90deg, #22d3ee, #60a5fa)',
                                    WebkitBackgroundClip: 'text',
                                    WebkitTextFillColor: 'transparent',
                                    backgroundClip: 'text'
                                }}>
                                    Network Monitor
                                </h1>
                                <p style={{ fontSize: '11px', color: '#94a3b8' }}>Real-time Infrastructure Insights</p>
                            </div>
                        </div>

                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '6px 12px',
                            borderRadius: '20px',
                            background: isConnected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                            color: isConnected ? '#10b981' : '#ef4444',
                            fontSize: '12px',
                            fontWeight: '500'
                        }}>
                            <div className="animate-pulse" style={{
                                width: '8px',
                                height: '8px',
                                borderRadius: '50%',
                                background: isConnected ? '#10b981' : '#ef4444'
                            }}></div>
                            <span>{isConnected ? 'Live' : 'Disconnected'}</span>
                        </div>
                    </div>
                </div>

                {/* Stats Bar */}
                <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '24px 24px 0' }}>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '16px'
                    }}>
                        <StatCard
                            icon={<Activity size={20} />}
                            label="Connections"
                            value={data.stats.total_connections || 0}
                            color="linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)"
                        />
                        <StatCard
                            icon={<Box size={20} />}
                            label="Containers"
                            value={data.stats.total_containers || 0}
                            color="linear-gradient(135deg, #a855f7 0%, #ec4899 100%)"
                        />
                        <StatCard
                            icon={<Zap size={20} />}
                            label="Open Ports"
                            value={data.stats.total_ports || 0}
                            color="linear-gradient(135deg, #f59e0b 0%, #f97316 100%)"
                        />
                        <StatCard
                            icon={<AlertTriangle size={20} />}
                            label="Anomalies"
                            value={data.anomalies.length}
                            color="linear-gradient(135deg, #ef4444 0%, #f43f5e 100%)"
                        />
                    </div>
                </div>

                {/* Navigation */}
                <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '24px 24px 0' }}>
                    <div style={{
                        display: 'flex',
                        gap: '8px',
                        background: 'rgba(30, 41, 59, 0.5)',
                        backdropFilter: 'blur(10px)',
                        borderRadius: '12px',
                        padding: '8px',
                        border: '1px solid rgba(148, 163, 184, 0.1)',
                        flexWrap: 'wrap'
                    }}>
                        {[
                            { id: 'topology', label: 'Topology', icon: <Network size={16} /> },
                            { id: 'connections', label: 'Connections', icon: <Activity size={16} /> },
                            { id: 'containers', label: 'Containers', icon: <Box size={16} /> },
                            { id: 'ports', label: 'Ports', icon: <Server size={16} /> },
                            { id: 'anomalies', label: 'Anomalies', icon: <AlertTriangle size={16} /> }
                        ].map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveView(tab.id)}
                                className="transition-all"
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    padding: '10px 16px',
                                    borderRadius: '8px',
                                    border: 'none',
                                    cursor: 'pointer',
                                    fontSize: '14px',
                                    fontWeight: '500',
                                    background: activeView === tab.id
                                        ? 'linear-gradient(90deg, #06b6d4, #3b82f6)'
                                        : 'transparent',
                                    color: activeView === tab.id ? '#fff' : '#94a3b8',
                                    boxShadow: activeView === tab.id ? '0 10px 30px rgba(6, 182, 212, 0.3)' : 'none'
                                }}
                                onMouseEnter={(e) => {
                                    if (activeView !== tab.id) {
                                        e.target.style.background = 'rgba(30, 41, 59, 0.8)';
                                        e.target.style.color = '#fff';
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (activeView !== tab.id) {
                                        e.target.style.background = 'transparent';
                                        e.target.style.color = '#94a3b8';
                                    }
                                }}
                            >
                                {tab.icon}
                                <span>{tab.label}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Main Content */}
                <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '24px' }}>
                    {activeView === 'topology' && <TopologyView data={data.topology} />}
                    {activeView === 'connections' && <ConnectionsView connections={data.connections} />}
                    {activeView === 'containers' && <ContainersView containers={data.containers} />}
                    {activeView === 'ports' && <PortsView ports={data.ports} />}
                    {activeView === 'anomalies' && <AnomaliesView anomalies={data.anomalies} />}
                </div>
            </div>
        </>
    );
};

export default NetworkDashboard;