import React from "react";

export default function Features() {
  const features = [
    {
      title: "🖼️ Image Forensics",
      desc: "Detect hidden manipulations using advanced image analysis techniques."
    },
    {
      title: "🤖 AI Detection",
      desc: "Deep learning models identify tampering patterns instantly."
    },
    {
      title: "📄 OCR Analysis",
      desc: "Extract and analyze text inconsistencies from documents."
    },
    {
      title: "📊 Risk Scoring",
      desc: "Get a final confidence score and fraud probability."
    },
    {
      title: "⚡ Fast Processing",
      desc: "Get results in seconds with optimized pipeline."
    },
    {
      title: "🔒 Secure Uploads",
      desc: "Files are auto-deleted after processing."
    }
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-16">

      <h1 className="text-4xl font-bold text-center mb-12">
        Features
      </h1>

      <div className="grid md:grid-cols-3 gap-8">
        {features.map((f, i) => (
          <div key={i} className="p-6 border rounded-xl shadow-sm hover:shadow-md transition">
            <h2 className="text-xl font-semibold mb-2">{f.title}</h2>
            <p className="text-gray-600">{f.desc}</p>
          </div>
        ))}
      </div>

    </div>
  );
}