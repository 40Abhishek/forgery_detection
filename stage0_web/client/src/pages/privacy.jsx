export default function Privacy() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12 text-gray-800 dark:text-gray-300">
      <h1 className="text-3xl font-bold mb-6">Privacy Policy</h1>

      <p className="mb-4">
        Your privacy is important to us. This document explains how your data is handled.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">1. File Uploads</h2>
      <p className="mb-4">
        Uploaded documents are used only for tampering detection and are not stored permanently.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">2. No Personal Tracking</h2>
      <p className="mb-4">
        We do not track personal user data or require login/signup.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">3. Security</h2>
      <p className="mb-4">
        Files are processed securely and deleted after processing to ensure confidentiality.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">4. Third-Party Services</h2>
      <p>
        We do not share your files with third-party services.
      </p>
    </div>
  );
}