import React from "react";
import { useLocation } from "react-router-dom";

export default function Result() {
  const location = useLocation();
  const results = location.state?.results || [];

  return (
    <div className="max-w-4xl mx-auto px-6 py-16">

      <h1 className="text-4xl font-bold text-center mb-10">
        Detection Results
      </h1>

      {results.length === 0 ? (
        <p className="text-center text-gray-500">
          No results available.
        </p>
      ) : (
        <div className="space-y-6">
          {results.map((res, index) => (
            <div
              key={index}
              className="p-6 border rounded-xl shadow-sm bg-white dark:bg-gray-900"
            >
              <p><strong>File:</strong> {res.filename}</p>

              <p>
                <strong>Status:</strong>{" "}
                <span className={
                  res.result === "FORGED"
                    ? "text-red-500"
                    : "text-green-500"
                }>
                  {res.result}
                </span>
              </p>

              <p><strong>Confidence:</strong> {res.confidence}%</p>

              <div className="w-full bg-gray-200 rounded-full h-3 mt-3">
                <div
                  className="bg-black h-3 rounded-full"
                  style={{ width: `${res.confidence}%` }}
                ></div>
              </div>

            </div>
          ))}
        </div>
      )}

    </div>
  );
}