import { useEffect, useState } from "react";

function App() {
  const [data, setData] = useState({ service: "loading...", env: "" });

  useEffect(() => {
    fetch("/api")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData({ service: "unreachable", env: "" }));
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>webapp</h1>
      <p>
        Backend service: <strong>{data.service}</strong>
      </p>
      <p>Environment: {data.env}</p>
    </main>
  );
}

export default App;
