import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

export default function Result() {
  const location = useLocation();
  const navigate = useNavigate();

  const response = location.state?.results;
  const results = response?.result;

  if (!results) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-center">
        <h2 className="text-2xl font-bold mb-4">No Results Found</h2>
        <button
          onClick={() => navigate("/")}
          className="bg-black text-white px-6 py-2 rounded-lg"
        >
          Go Back
        </button>
      </div>
    );
  }

  const rawName = results.file?.name || "";
  const fileName = rawName.replace(/^\d+-/, "") || "N/A";
  const verdict = results.verdict || "UNKNOWN";
  const riskScore = results.risk_score ?? "N/A";
  const riskLevel = results.risk_level || "N/A";

  const forensics = results.breakdown?.forensics_score ?? "N/A";
  const cnn = results.breakdown?.cnn_score ?? "N/A";
  const ocr = results.breakdown?.ocr_score ?? "N/A";

  const anomalies = Array.isArray(results.anomalies)
    ? results.anomalies
    : [];

  return (
    <div className="max-w-4xl mx-auto px-6 py-16">

      <h1 className="text-4xl font-bold text-center mb-10">
        Detection Results
      </h1>

      <div className="space-y-6">

        {/* MAIN CARD */}
        <div className="p-6 border rounded-xl bg-white dark:bg-gray-900">
          <h2 className="text-xl font-bold mb-4">🔍 Analysis Result</h2>

          <p><b>File:</b> {fileName}</p>

          <p>
            <b>Verdict:</b>
            <span
              className={`ml-2 font-bold ${
                verdict === "FORGED"
                  ? "text-red-500"
                  : verdict === "SUSPICIOUS"
                  ? "text-yellow-500"
                  : "text-green-500"
              }`}
            >
              {verdict}
            </span>
          </p>

          <p><b>Risk Score:</b> {riskScore}</p>
          <p><b>Risk Level:</b> {riskLevel}</p>
        </div>

        {/* BREAKDOWN */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold">Forensics</h3>
            <p>{forensics}</p>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold">CNN</h3>
            <p>{cnn}</p>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold">OCR</h3>
            <p>{ocr}</p>
          </div>
        </div>

        {/* ANOMALIES */}
        <div className="p-4 border rounded-lg">
          <h3 className="font-bold mb-2">⚠️ Anomalies</h3>

          {anomalies.length > 0 ? (
            anomalies.map((a, i) => (
              <div key={i} className="text-sm mb-2">
                <b>{a.stage}</b> → {a.detail}
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-500">
              No anomalies detected
            </p>
          )}
        </div>

      </div>
    </div>
  );
}