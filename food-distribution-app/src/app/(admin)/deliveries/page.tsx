'use client';

import { useEffect, useState } from "react";
import { useFetch } from "@/src/util/useFetch";
import { getColumns } from "@/src/components/DataTable/getColumns";
import { Recipient } from "@/src/types/Recipient";
import { DataTable } from "@/src/components/DataTable/DataTable"
import { SearchBar } from "@/src/components/SearchBar/SearchBar";

import styles from "./styles.module.css";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function DeliveriesPage() {
    const [searchTerm, setSearchTerm] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [sortBy, setSortBy] = useState('');
    const [sortAscending, setSortAscending] = useState(true);

    // Fetch when the search changes
        // Debounced so it doesn't search on every keystroke
        // Will search after 300ms of idle time
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchTerm);
        }, 300);

        return () => {
            clearTimeout(timer);
        }
    }, [searchTerm]);

    const { data, isLoading, error } = useFetch<Recipient[]>(
        `${apiUrl}?query=${encodeURIComponent(debouncedSearch)}`
    );

    // Set the values you want to display on the table
    const columns = getColumns<Recipient>(data?.result ?? []);

    // Handle sorting


    return (
        <>
            <h1 className={styles.header}>Deliveries</h1>
            <div className={styles.tableGroup}>
                <SearchBar
                    value={searchTerm}
                    columns={columns}
                    sortByValue={sortBy}
                    setSortByValue={setSortBy}
                    sortAscending={sortAscending}
                    setSortAscending={setSortAscending}
                    handleSearch={setSearchTerm}
                />
                <DataTable
                    data={data?.result ?? []}
                    columns={columns}
                    isLoading={isLoading}
                    error={error}
                />
            </div>
        </>
    )
}