export default function Contact() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-12 text-gray-800 dark:text-gray-300">

      <h1 className="text-3xl font-bold text-center mb-10">Contact Us</h1>

      <div className="grid md:grid-cols-2 gap-8">

        {/* Bharat Card */}
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl p-6 shadow hover:shadow-lg transition">

          {/* Image */}
          <div className="flex justify-center mb-4">
            <img
              src=""
              alt="Bharat"
              className="w-28 h-28 rounded-full object-cover border-4 border-gray-200 dark:border-gray-700"
            />
          </div>

          <h2 className="text-xl font-semibold text-center mb-2">Bharat Swami</h2>
          <p className="text-sm text-center mb-4">MCA 4th Sem</p>

          <div className="text-sm space-y-2 text-center">
            <p>📧 swamibharat2110@gmail.com</p>
            <p>📞 8892634444</p>
            <p>📍 CUH, CS&IT Department</p>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl p-6 shadow hover:shadow-lg transition">

          <div className="flex justify-center mb-4">
            <img
              src="https://via.placeholder.com/120"
              alt="Abhishek"
              className="w-28 h-28 rounded-full object-cover border-4 border-gray-200 dark:border-gray-700"
            />
          </div>

          <h2 className="text-xl font-semibold text-center mb-2">Abhishek Yadav</h2>
          <p className="text-sm text-center mb-4">MCA 4th Sem</p>

          <div className="text-sm space-y-2 text-center">
            <p>📧 abhishekyadav40@gmail.com</p>
            <p>📞 9053266969</p>
            <p>📍 CUH, CS&IT Department</p>
          </div>
        </div>

      </div>
    </div>
  );
}