import React from "react";
import { ShieldCheck, Upload, Layers, Zap } from "lucide-react";

const features = [
  {
    icon: <Upload size={40} />,
    title: "Upload Images or PDFs",
    description:
      "Easily upload documents in image or PDF format. Our system instantly prepares files for advanced verification.",
  },
  {
    icon: <Zap size={40} />,
    title: "Detect Tampering in Seconds",
    description:
      "AI-powered analysis quickly identifies edits, manipulations, and suspicious modifications within seconds.",
  },
  {
    icon: <Layers size={40} />,
    title: "Multiple Verification Layers",
    description:
      "Advanced multi-layer validation combines metadata analysis, visual inspection, and pattern recognition.",
  },
  {
    icon: <ShieldCheck size={40} />,
    title: "High Accuracy & Security",
    description:
      "Enterprise-grade detection ensures reliable results while keeping your documents safe and private.",
  },
];

export default function Features() {
  return (
    <div className="min-h-screen bg-gray-50 py-16 px-6">
      {/* Header */}
      <div className="text-center max-w-3xl mx-auto mb-14">
        <h1 className="text-4xl font-bold text-gray-900">
          Powerful Document Verification
        </h1>

        <p className="mt-4 text-lg text-gray-600">
          Upload images or PDFs and detect tampering in seconds.
          Multiple verification layers ensure high accuracy.
          Try it now and experience the future of document security!
        </p>
      </div>

      {/* Features Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-6xl mx-auto">
        {features.map((feature, index) => (
          <div
            key={index}
            className="bg-white p-8 rounded-2xl shadow-md hover:shadow-xl transition duration-300"
          >
            <div className="text-blue-600 mb-4">{feature.icon}</div>

            <h3 className="text-xl font-semibold mb-2">
              {feature.title}
            </h3>

            <p className="text-gray-600">
              {feature.description}
            </p>
          </div>
        ))}
      </div>

      {/* CTA Section */}
      <div className="text-center mt-20">
        <h2 className="text-3xl font-bold text-gray-900">
          Ready to Secure Your Documents?
        </h2>

        <p className="text-gray-600 mt-3">
          Start verifying documents instantly with our smart detection system.
        </p>

        <button className="mt-6 bg-blue-600 text-white px-8 py-3 rounded-xl hover:bg-blue-700 transition">
          Try It Now
        </button>
      </div>
    </div>
  );
}