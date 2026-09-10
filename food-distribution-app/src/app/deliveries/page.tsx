"use client";

import { ArrowDown, ArrowUp, Filter, Pencil, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { PriorityLevels, type PriorityLevel } from "@/src/components/ui/PriorityLevels";

type RecipientSite = {
  id: string;
  name: string;
  priority: number;
  is_active: boolean;
  is_fallback: boolean;
  capacity_level: number | null;
  food_type: string[];
};

type SortMode = "priority" | "name";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function toPriorityLevel(priority: number): PriorityLevel {
  return String(Math.min(5, Math.max(1, priority))) as PriorityLevel;
}

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<RecipientSite[]>([]);
  const [query, setQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("priority");
  const [priorityAscending, setPriorityAscending] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const includeInactive = showInactive ? "?include_inactive=true" : "";

    fetch(`${apiUrl}/api/v1/recipient-sites${includeInactive}`, {
      signal: controller.signal,
      cache: "no-store",
    })
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load profiles");
        return response.json() as Promise<RecipientSite[]>;
      })
      .then((data) => {
        setProfiles(data);
        setError("");
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setError("Could not connect to the recipient database.");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [showInactive]);

  const visibleProfiles = useMemo(() => profiles
    .filter((profile) => profile.name.toLowerCase().includes(query.trim().toLowerCase()))
    .sort((first, second) => {
      if (sortMode === "name") return first.name.localeCompare(second.name);
      const priorityResult = first.priority - second.priority;
      return (priorityAscending ? priorityResult : -priorityResult) || first.name.localeCompare(second.name);
    }), [profiles, priorityAscending, query, sortMode]);

  return (
    <div className="min-h-full bg-white px-[22px] py-7 text-[#151515] sm:px-7 lg:px-[22px] lg:py-7">
      <header className="mb-1">
        <h1 className="text-[27px] font-normal leading-none tracking-[-0.6px]">Profiles</h1>
        <p className="mt-2 text-[15px] leading-none text-[#969696]">
          {loading ? "Loading profiles..." : `Showing ${visibleProfiles.length} of ${profiles.length} profiles`}
        </p>
      </header>

      <section className="mt-[10px] min-h-[552px] rounded-[19px] border border-[#dedede] bg-[#fcfcfc] p-[17px] sm:p-[18px]">
        <div className="mb-[13px] flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-4">
            <label className="flex h-8 w-[146px] items-center gap-3 rounded-[15px] border border-[#d1d1d1] bg-white px-3 text-[14px] text-[#3e3e3e]">
              <Search className="h-[15px] w-[15px] text-[#d1d1d1]" />
              <span className="sr-only">Search profiles</span>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search" className="w-full bg-transparent outline-none placeholder:text-[#3e3e3e]" />
            </label>
            <label className="flex h-8 items-center gap-2 rounded-[15px] border border-[#d1d1d1] bg-white px-3 text-[14px] text-[#3e3e3e]">
              <span className="h-3 w-3 rounded-full bg-[#d7d7d7]" />
              <span className="sr-only">Sort profiles</span>
              <select aria-label="Sort profiles" value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)} className="appearance-none bg-transparent outline-none">
                <option value="priority">Sort</option>
                <option value="priority">Priority</option>
                <option value="name">Name</option>
              </select>
            </label>
            <button type="button" onClick={() => { setLoading(true); setShowInactive((visible) => !visible); }} className={`flex h-8 items-center gap-2 rounded-[15px] border px-3 text-[14px] transition-colors ${showInactive ? "border-[#4a4a4a] bg-[#4a4a4a] text-white" : "border-[#d1d1d1] bg-white text-[#3e3e3e]"}`}>
              <Filter className="h-[14px] w-[14px]" />Filter
            </button>
          </div>
          <div className="flex items-center gap-3">
            <button type="button" aria-label="Edit profiles" title="Edit profiles" className="flex h-8 items-center gap-2 rounded-[14px] bg-[#4a4a4a] px-4 text-[14px] text-white"><Pencil className="h-[13px] w-[13px]" />Edit</button>
            <button type="button" aria-label="Add profile" title="Add profile" className="flex h-8 items-center gap-2 rounded-[14px] bg-black px-3 text-[14px] text-white"><Plus className="h-[14px] w-[14px]" />Add Profile</button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[690px] table-fixed text-[12px]">
            <colgroup><col className="w-[27%]" /><col className="w-[21%]" /><col className="w-[15%]" /><col className="w-[13%]" /><col className="w-[24%]" /></colgroup>
            <thead>
              <tr className="h-[38px] bg-[#e7e7e7] text-[14px] text-[#414141]">
                <th className="rounded-l-[10px] px-4 text-left font-normal">Organization Name</th>
                <th className="px-3 text-center font-normal">
                  <button type="button" aria-label="Sort by priority" aria-pressed={sortMode === "priority"} onClick={() => { setSortMode("priority"); setPriorityAscending((ascending) => !ascending); }} className={`inline-flex items-center gap-1 ${sortMode === "priority" ? "text-[#151515]" : "text-[#8a8a8a]"}`}>
                    Priority Level
                    {priorityAscending ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
                  </button>
                </th>
                <th className="px-3 text-center font-normal">Location</th>
                <th className="px-3 text-center font-normal">Capacity Level</th>
                <th className="rounded-r-[10px] px-3 text-center font-normal">Food Type</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={5} className="h-28 text-center text-[#777]">Loading profiles...</td></tr>}
              {!loading && error && <tr><td colSpan={5} className="h-28 text-center text-[#777]">{error}</td></tr>}
              {!loading && !error && visibleProfiles.map((profile) => (
                <tr key={profile.id} className="h-[47px] border-b border-[#e9e9e9] text-[#151515]">
                  <td className="px-4">{profile.name}</td>
                  <td className="px-3"><PriorityLevels property1={toPriorityLevel(profile.priority)} className="mx-auto" /></td>
                  <td className="px-3 text-center">--</td>
                  <td className="px-3 text-center">{profile.capacity_level ?? "--"}</td>
                  <td className="px-3 text-center">{profile.food_type.length > 0 ? profile.food_type.join(", ") : "--"}</td>
                </tr>
              ))}
              {!loading && !error && visibleProfiles.length === 0 && <tr><td colSpan={5} className="h-28 text-center text-[#777]">No profiles match your search.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
