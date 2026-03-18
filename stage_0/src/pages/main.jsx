import React from 'react'
import FileUploader from "./FileUploader";
import Introduction from "./Introduction";

const main = () => {
  return (
    <div>
      <main className="grow">

       
        <section className="px-6 py-20">
          <div className="max-w-7xl mx-auto">

            <div className="grid md:grid-cols-2 gap-16 items-center">

            <div className="space-y-8">
             <Introduction />
            </div>

            <div className="flex justify-center md:justify-end">
            <div className="w-full max-w-xl">
                  <FileUploader />
            </div>
            </div>

            </div>

          </div>
        </section>

      </main>
    </div>
  )
}

export default main
