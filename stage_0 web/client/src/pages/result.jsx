import React, { useEffect, useState } from "react";
import { fetchResults } from "../services/api";

export default function Results() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetchResults().then(setData);
  }, []);

  return (
    <div>
      <h2>Past Results</h2>

      {data.map((item) => (
        <div key={item._id}>
          <h4>{item.originalName}</h4>
          <p>{item.result}</p>
          <p>{item.confidence}%</p>
        </div>
      ))}
    </div>
  );
}