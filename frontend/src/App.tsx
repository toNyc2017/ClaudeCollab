import React, { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    // For development
    const baseUrl = process.env.NODE_ENV === 'development' 
      ? 'http://localhost:5000'
      : 'https://tonyc2017.github.io/ClaudeCollab';

    setMessage("Hello from React! This is a static message since we're running on GitHub Pages.");
    
    // Commented out the API call since GitHub Pages only serves static content
    /*
    axios.get(`${baseUrl}`)
      .then(response => {
        setMessage(response.data.message);
      })
      .catch(error => {
        console.error("Error fetching message:", error);
        setMessage("Error connecting to backend");
      });
    */
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <p>{message || "Loading..."}</p>
      </header>
    </div>
  );
}

export default App;
