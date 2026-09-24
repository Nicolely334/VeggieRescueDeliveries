'use client';

import { useEffect, useState } from "react";
import { useFetch } from "@/src/util/useFetch";
import { Delivery } from "@/src/types/Delivery";
import { Column, DataTable } from "@/src/components/DataTable/DataTable"
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

    const { data, isLoading, error } = useFetch<Delivery[]>(
        // `${apiUrl}?query=${encodeURIComponent(debouncedSearch)}`
        `${apiUrl}/api/v1/deliveries?limit=${50}&offset=${0}&sort=${'newest'}`
    );

    // Set the values you want to display on the table
    const columns: Column<Delivery>[] = [
        {key: "delivery_date", header: "Date"}, 
        {key: "recipient", header: "Recipient"},
        {key: "location", header: "Location"},
        {key: "produce_pounds", header: "Produce (lbs.)"},
        {key: "packaged_pounds", header: "Packaged (lbs.)"},
        {key: "driver", header: "Driver"},
        {key: "vehicle", header: "Vehicle"}
    ]

    // Handle sorting


    return (
        <>
            <h1 className={styles.header}>Deliveries</h1>
            <div className={styles.tableGroup}>
                <SearchBar<Delivery>
                    searchValue={searchTerm}
                    columns={columns}
                    sortByValue={sortBy}
                    setSortByValue={setSortBy}
                    sortAscending={sortAscending}
                    setSortAscending={setSortAscending}
                    handleSearch={setSearchTerm}
                />
                <DataTable<Delivery>
                    data={data?.result ?? []}
                    columns={columns}
                    isLoading={isLoading}
                    error={error}
                />
            </div>
        </>
    )
}