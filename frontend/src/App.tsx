import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [message, setMessage] = useState('');

  useEffect(() => {
    axios.get('http://localhost:5000')
      .then(response => {
        setMessage(response.data.message);
      })
      .catch(error => {
        console.error('Error fetching message:', error);
        setMessage('Error connecting to backend');
      });
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <p>{message || 'Loading...'}</p>
      </header>
    </div>
  );
}

export default App;
