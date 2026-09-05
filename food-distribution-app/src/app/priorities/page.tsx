"use client";

import { ArrowDown, ArrowUp, Circle, Filter, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type Delivery = {
  id: string;
  delivery_date: string;
  recipient: string;
  location: string;
  produce_pounds: number | null;
  packaged_pounds: number | null;
  driver: string;
  vehicle: string;
  status: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatPounds(value: number | null) {
  return value === null ? "-" : `${value.toLocaleString()} lbs`;
}

export default function AllDeliveriesPage() {
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [query, setQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [sortAscending, setSortAscending] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${apiUrl}/api/v1/deliveries`)
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load deliveries");
        return response.json() as Promise<{ deliveries: Delivery[] }>;
      })
      .then((data) => setDeliveries(data.deliveries))
      .catch(() => setError("Could not connect to the delivery database."))
      .finally(() => setLoading(false));
  }, []);

  const statuses = useMemo(() => [...new Set(deliveries.map((delivery) => delivery.status))], [deliveries]);
  const visibleDeliveries = useMemo(() => deliveries
    .filter((delivery) => statusFilter === "all" || delivery.status === statusFilter)
    .filter((delivery) => `${delivery.recipient} ${delivery.location} ${delivery.driver} ${delivery.vehicle}`.toLowerCase().includes(query.toLowerCase()))
    .sort((first, second) => {
      const result = first.delivery_date.localeCompare(second.delivery_date);
      return sortAscending ? result : -result;
    }), [deliveries, query, sortAscending, statusFilter]);

  return (
    <div className="min-h-full bg-[#fcfcfc] px-5 py-6 text-[#151515] sm:px-7 lg:px-8 lg:py-7">
      <div className="rounded-[25px] border-2 border-[#cccccc]/35 bg-[#ebebeb]/25 p-4 sm:p-6">
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-3">
            <label className="flex h-9 w-[204px] items-center gap-3 rounded-[18px] border border-[#cccccc] bg-white px-4 text-[16px] text-[#343434]">
              <Search className="h-4 w-4 text-[#cfcfcf]" /><span className="sr-only">Search deliveries</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search" className="w-full bg-transparent outline-none placeholder:text-[#343434]" />
            </label>
            <button type="button" onClick={() => setSortAscending((ascending) => !ascending)} className="flex h-9 items-center gap-3 rounded-[18px] border border-[#cccccc] bg-white px-4 text-[16px] text-[#343434]"><Circle className="h-3 w-3 fill-[#d4d4d4] text-[#d4d4d4]" />Sort {sortAscending ? "↑" : "↓"}</button>
            <button type="button" onClick={() => setShowFilters((visible) => !visible)} className="flex h-9 items-center gap-3 rounded-[18px] border border-[#cccccc] bg-white px-4 text-[16px] text-[#343434]"><Filter className="h-4 w-4" />Filter</button>
            {showFilters && <select aria-label="Filter by status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="h-9 rounded-[18px] border border-[#cccccc] bg-white px-3 text-[14px]"><option value="all">All statuses</option>{statuses.map((status) => <option key={status} value={status}>{status}</option>)}</select>}
          </div>
          <button type="button" className="rounded-[18px] bg-black px-4 py-2 text-[16px] text-[#cccccc]">+ Add Delivery</button>
        </header>

        <div className="overflow-x-auto rounded-[15px]">
          <table className="w-full min-w-[900px] table-fixed text-[14px]">
            <colgroup><col className="w-[12%]" /><col className="w-[27%]" /><col className="w-[18%]" /><col className="w-[13%]" /><col className="w-[13%]" /><col className="w-[10%]" /><col className="w-[12%]" /></colgroup>
            <thead><tr className="h-[40px] rounded-[15px] bg-[#cccccc]/35 text-left text-[#343434]"><th className="rounded-l-[15px] px-4 font-normal">Date <button type="button" aria-label="Toggle date sort" onClick={() => setSortAscending((ascending) => !ascending)}>{sortAscending ? <ArrowUp className="inline h-3 w-3" /> : <ArrowDown className="inline h-3 w-3" />}</button></th><th className="px-4 font-normal">Recipient</th><th className="px-4 font-normal">Location</th><th className="px-4 text-center font-normal">Produce</th><th className="px-4 text-center font-normal">Packaged</th><th className="px-4 text-center font-normal">Driver</th><th className="rounded-r-[15px] px-4 text-center font-normal">Vehicle</th></tr></thead>
            <tbody>{loading && <tr><td colSpan={7} className="h-32 text-center text-[#666]">Loading deliveries...</td></tr>}{error && !loading && <tr><td colSpan={7} className="h-32 text-center text-[#666]">{error}</td></tr>}{!loading && !error && visibleDeliveries.map((delivery) => <tr key={delivery.id} className="h-[51px] border-b border-[#cccccc]/35"><td className="border-r border-[#cccccc]/60 px-4 align-top pt-3">{formatDate(delivery.delivery_date)}</td><td className="px-4 align-top pt-3">{delivery.recipient || "-"}</td><td className="px-4 align-top pt-3">{delivery.location || "-"}</td><td className="px-4 text-center align-top pt-3">{formatPounds(delivery.produce_pounds)}</td><td className="px-4 text-center align-top pt-3">{formatPounds(delivery.packaged_pounds)}</td><td className="px-4 text-center align-top pt-3">{delivery.driver || "-"}</td><td className="px-4 text-center align-top pt-3">{delivery.vehicle || "-"}</td></tr>)}{!loading && !error && visibleDeliveries.length === 0 && <tr><td colSpan={7} className="h-32 text-center text-[#666]">No deliveries match your search.</td></tr>}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
