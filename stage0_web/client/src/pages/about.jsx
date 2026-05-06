import React from "react";

export default function About() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-16">

      <h1 className="text-4xl font-bold mb-6 text-center">
        About Our System
      </h1>

      <p className="text-lg text-gray-600 text-center mb-10">
        Our Document Forgery Detection System is designed to identify tampered 
        images and documents using advanced machine learning and forensic techniques.
      </p>

      <div className="grid md:grid-cols-2 gap-8">

        <div className="p-6 border rounded-xl shadow-sm">
          <h2 className="text-xl font-semibold mb-2">🎯 Our Mission</h2>
          <p className="text-gray-600">
            To provide a fast, reliable, and intelligent solution to detect
            forged or manipulated documents in seconds.
          </p>
        </div>

        <div className="p-6 border rounded-xl shadow-sm">
          <h2 className="text-xl font-semibold mb-2">🧠 Technology</h2>
          <p className="text-gray-600">
            We combine image forensics, deep learning models, OCR analysis,
            and risk scoring to deliver highly accurate results.
          </p>
        </div>

        <div className="p-6 border rounded-xl shadow-sm">
          <h2 className="text-xl font-semibold mb-2">⚡ Speed</h2>
          <p className="text-gray-600">
            Get results in seconds with our optimized pipeline.
          </p>
        </div>

        <div className="p-6 border rounded-xl shadow-sm">
          <h2 className="text-xl font-semibold mb-2">🔒 Security</h2>
          <p className="text-gray-600">
            Your files are processed securely and removed after analysis.
          </p>
        </div>

      </div>
    </div>
  );
}