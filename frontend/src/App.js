import React, { useEffect, useState } from 'react';

function App() {
  const [data, setData] = useState(null);

  useEffect(() => {
    // פנייה ל-Backend
    fetch('http://backend:8000/api/hello')
      .then(response => response.json())
      .then(data => setData(data))
      .catch(err => console.error("Error fetching data:", err));
  }, []);

  return (
    <div style={{ padding: '50px', fontFamily: 'Arial' }}>
      <h1>Production Dashboard</h1>
      <hr />
      {data ? (
        <div>
          <h2>Status: <span style={{color: 'green'}}>Online</span></h2>
          <p>Message: {data.message}</p>
          <p>Database: <b>{data.database_status}</b></p>
          <p>Version: {data.version}</p>
        </div>
      ) : (
        <p>Loading backend data...</p>
      )}
    </div>
  );
}

export default App;
