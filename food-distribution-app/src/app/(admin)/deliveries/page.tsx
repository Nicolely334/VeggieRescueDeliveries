'use client';

import { useEffect, useState } from "react";
import { useFetch } from "@/src/util/useFetch";
import { ApiResponse } from "@/src/util/types/ApiResponse";
import { Recipient } from "@/src/types/Recipient";
import { DataTable } from "@/src/components/DataTable/DataTable"
import { SearchBar } from "@/src/components/SearchBar/SearchBar";

import styles from "./styles.module.css";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ProfilesPage() {
    const [searchTerm, setSearchTerm] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');

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

    // Assumes that the data returned is a JSON object containing a property
        // with the specified array
    const { data, isLoading, error } = useFetch<ApiResponse<Recipient[]>>(
        `${apiUrl}?query=${encodeURIComponent(debouncedSearch)}`
    );

    return (
        <section className={styles.container}>
            <SearchBar
                value={searchTerm}
                handleSearch={setSearchTerm}
            />
            <DataTable
                data={data.result}
                columns={columns}
                isLoading={isLoading}
                error={error}
            />
        </section>
    )
}