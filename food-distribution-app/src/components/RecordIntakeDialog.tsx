"use client";

import { useState } from "react";
import { ChevronDown, X } from "lucide-react";

const fieldClass = "h-[39px] rounded-[15px] bg-[#ececec] px-4 text-[16px] text-[#343434] outline-none placeholder:text-[#7b7b7b] focus:ring-2 focus:ring-[#202020]/20";

function FoodRow({ type, amount }: { type: string; amount: string }) {
  return (
    <div className="grid grid-cols-[1.35fr_1fr_.86fr] items-center gap-6">
      <button type="button" className={`${fieldClass} text-center`}>{type}</button>
      <input aria-label={`${type} amount`} className={`${fieldClass} text-center`} defaultValue={amount} />
      <button type="button" className={`${fieldClass} flex items-center justify-center gap-1`}>lbs <ChevronDown className="h-3 w-3" /></button>
    </div>
  );
}

export function RecordIntakeDialog() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button onClick={() => setOpen(true)} className="rounded-full bg-[#202020] px-[13px] py-[7px] text-[14px] text-white transition hover:bg-black">+ Record Food Intake</button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
          <section role="dialog" aria-modal="true" aria-labelledby="record-intake-title" className="max-h-[calc(100vh-32px)] w-full max-w-[730px] overflow-y-auto rounded-[25px] bg-white px-9 py-9 text-black shadow-xl sm:px-[43px] sm:py-[39px]">
            <div className="flex items-start justify-between gap-4">
              <h2 id="record-intake-title" className="text-[30px] font-normal leading-tight">Record Today’s Food Intake</h2>
              <button aria-label="Close" onClick={() => setOpen(false)} className="shrink-0 text-[#979797] transition hover:text-black"><X className="h-8 w-8" strokeWidth={2.5} /></button>
            </div>

            <form onSubmit={(event) => { event.preventDefault(); setOpen(false); }}>
              <div className="mt-[46px] space-y-[27px]">
                <label className="block text-[20px] font-medium">Date *<input type="date" className={`${fieldClass} mt-[15px] block w-full`} /></label>
                <label className="block text-[20px] font-medium">Donor Name *<input className={`${fieldClass} mt-[15px] block w-full`} /></label>
              </div>

              <fieldset className="mt-[31px] border-0 p-0">
                <legend className="text-[20px] font-medium">Food Received *</legend>
                <div className="mt-[27px] grid grid-cols-[1.35fr_1fr_.86fr] gap-6 px-3 text-center text-[16px] text-[#343434]">
                  <span>Food Type</span><span>Amount</span><span>Unit</span>
                </div>
                <div className="mt-[9px] space-y-5 px-3"><FoodRow type="Produce" amount="150" /><FoodRow type="Packaged" amount="150" /></div>
                <button type="button" className="mt-5 rounded-[15px] bg-[#ececec] px-5 py-[9px] text-[16px] text-[#7b7b7b]">+ Add Food Type</button>
              </fieldset>

              <label className="mt-[31px] block text-[20px] font-medium">Notes<textarea className="mt-[15px] block h-[91px] w-full resize-none rounded-[15px] bg-[#ececec] p-4 text-[16px] outline-none focus:ring-2 focus:ring-[#202020]/20" /></label>
              <div className="mt-9 flex justify-end gap-[18px]">
                <button type="button" onClick={() => setOpen(false)} className="h-[46px] w-[136px] rounded-[20px] bg-[#979797] text-[20px] text-white transition hover:bg-[#777]">Cancel</button>
                <button type="submit" className="h-[46px] w-[136px] rounded-[20px] bg-[#1e1e1e] text-[20px] text-white transition hover:bg-black">Submit</button>
              </div>
            </form>
          </section>
        </div>
      )}
    </>
  );
}