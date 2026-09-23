import { useState, useEffect } from "react";
import { ApiResponse } from "./types/ApiResponse";

/*
    Usage:
    Use this hook to add fetching capabilities to the page you're working on

    **Note: When using this hook, you must type-check the data yourself on the page.
            It is meant to be a generic fetch, capable of grabbing any type of data,
            so you must be the one to validate it.
*/


export function useFetch<T = unknown>(url: string) {
    const [data, setData] = useState<ApiResponse<T> | undefined>(undefined);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | undefined>(undefined);

    useEffect(() => {
        const normalizedUrl = url.trim();

        // Avoid fetching on invalid URLs
        if (normalizedUrl === '') {
            setIsLoading(false);
            setError(undefined);
            setData(undefined);

            return;
        }

        const abortController = new AbortController();

        setIsLoading(true);
        setError(undefined);

        async function fetchData() {
            try {

                const response = await fetch(normalizedUrl, {
                    signal: abortController.signal
                });

                if (!response.ok) {
                    throw new Error('Unable to fetch data.');
                }

                const payload = await response.json();

                setData(payload);
            }
            catch (err) {
                if ((err as Error).name !== 'AbortError')
                    setError((err as Error).message ?? 'Unknown error occurred.');
            }
            finally {
                if (!abortController.signal.aborted)
                    setIsLoading(false);
            }
        }

        fetchData();

        return () => {
            abortController.abort();
        }
    }, [url])

    return { data, isLoading, error };
}