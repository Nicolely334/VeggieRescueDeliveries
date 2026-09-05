import { ArrowRight, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { RecordIntakeDialog } from "@/src/components/RecordIntakeDialog";

const priorities = [
  ["Isla Vista Youth Projects Kitchen / Preschool", "5", "15 LBS", "15 LBS", "Kevin", "Van", "Reviewed"],
  ["People Helping People", "5", "15 LBS", "15 LBS", "Kevin", "Van", "Reviewed"],
  ["BSC - Buellton Senior Center", "4", "9 LBS", "9 LBS", "Olga", "Van", "Needs Review*"],
];

const deliveries = [
  ["Isla Vista Youth Projects Kitchen / Preschool", "15 LBS", "15 LBS", "Kevin", "Van", "Assigned"],
  ["People Helping People", "15 LBS", "15 LBS", "Kevin", "Van", "Assigned"],
];

function RecipientName({ name }: { name: string }) {
  const [firstLine, secondLine] = name.split(" Kitchen /");
  return <span>{secondLine ? <>{firstLine}<br />Kitchen /{secondLine}</> : name}</span>;
}

function DashboardTable({ rows, headers }: { rows: string[][]; headers: string[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] table-fixed border-separate border-spacing-0 text-[12px] leading-[1.25]">
        <colgroup>
          <col className={headers.length === 7 ? "w-[21%]" : "w-[27%]"} />
          {headers.slice(1).map((header) => <col key={header} />)}
        </colgroup>
        <thead>
          <tr className="h-[38px] bg-[#e9e9e9] text-[14px] font-normal text-[#414141]">
            <th className="rounded-l-[9px] px-4 text-left font-normal">{headers[0]}</th>
            {headers.slice(1).map((header, index) => <th key={header} className={`px-3 text-center font-normal ${index === headers.length - 2 ? "rounded-r-[9px]" : ""}`}>{header}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={row[0]} className="h-[47px] text-[#151515]">
              <td className="max-w-0 overflow-hidden px-1 text-left"><div className="flex min-w-0 items-start gap-3"><span className="shrink-0">{index + 1}.</span><span className="min-w-0 break-words"><RecipientName name={row[0]} /></span></div></td>
              {row.slice(1).map((value, valueIndex) => <td key={`${row[0]}-${valueIndex}`} className="whitespace-nowrap px-3 text-center">{value}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Home() {
  return (
    <div className="min-h-full bg-white px-5 py-6 text-[#151515] sm:px-7 lg:px-7 lg:py-6">
      <header className="border-b border-[#d6d6d6] pb-[9px]">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-[26px] font-normal leading-none tracking-[-0.5px]">Today’s Dashboard</h1>
          <time className="text-[17px] text-[#505050]">September 2, 2026</time>
        </div>
      </header>

      <main>
        <div className="flex items-center justify-between py-[15px]">
          <h2 className="text-[18px] font-normal">Current Overview</h2>
          <RecordIntakeDialog />
        </div>

        <section className="grid gap-5 px-0 pb-[37px] sm:grid-cols-2 sm:px-7 lg:gap-[52px] lg:px-7">
          <div className="rounded-[7px] bg-[#ededed] px-4 py-[11px]">
            <h3 className="text-[14px] font-normal text-[#4e4e4e]">Daily Intake Allocation</h3>
            <p className="py-[17px] text-center text-[24px] leading-none">78 lbs Received</p>
            <div className="h-[11px] rounded-full bg-white"><div className="h-full w-[77%] rounded-full bg-[#353535]" /></div>
            <div className="flex justify-between pt-[5px] text-[12px] text-[#383838]"><span>Allocated: 60 lbs (77%)</span><span className="text-[#888]">Unallocated: 18 lbs (23%)</span></div>
          </div>
          <div className="rounded-[7px] bg-[#ededed] px-4 py-[11px]">
            <h3 className="text-[14px] font-normal text-[#4e4e4e]">Needs Attention</h3>
            <div className="space-y-[15px] pt-[27px] text-[12px]">
              <div className="flex items-center justify-between gap-4"><span className="flex items-center gap-1"><TriangleAlert className="h-3 w-3 fill-black" />18 lbs still unallocated</span><a href="#allocation" className="underline">Review <ArrowRight className="inline h-3 w-3" /></a></div>
              <div className="flex items-center justify-between gap-4"><span className="flex items-center gap-1"><TriangleAlert className="h-3 w-3 fill-black" />1 recommendations need review</span><a href="#priorities" className="underline">Review <ArrowRight className="inline h-3 w-3" /></a></div>
            </div>
          </div>
        </section>

        <section id="priorities" className="pb-[21px]">
          <div className="mb-[14px] flex items-center justify-between gap-4"><div className="flex items-baseline gap-3"><h2 className="text-[18px] font-normal">Today’s Priority Recommendations</h2><span className="text-[12px] text-[#888]">3 of 10 shown</span></div><button className="rounded-full bg-[#202020] px-[13px] py-[7px] text-[14px] text-white">View Full Queue <ArrowRight className="inline h-4 w-4" /></button></div>
          <DashboardTable headers={["Recipient", "Priority", "Produce", "Packaged", "Driver", "Vehicle", "Status"]} rows={priorities} />
        </section>

        <section>
          <div className="mb-[14px] flex items-center justify-between"><h2 className="text-[18px] font-normal">Today’s Deliveries</h2><Link href="/priorities" className="rounded-full bg-[#202020] px-[22px] py-[7px] text-[14px] text-white">View All</Link></div>
          <DashboardTable headers={["Recipient", "Produce", "Packaged", "Driver", "Vehicle", "Status"]} rows={deliveries} />
        </section>
      </main>
    </div>
  );
}
