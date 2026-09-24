import styles from "./styles.module.css";

export interface Column<T> {
    header: string,
    key: keyof T
}

interface DataTableProps<T> {
    data: T[],
    columns: Column<T>[],
    isLoading: boolean,
    error: string | undefined
}

export function DataTable<T>({ data, columns, isLoading, error }: DataTableProps<T>) {
    let message = '';

    if (isLoading) { 
        message = "Loading data...";
    } else if (error) {
        message = `Error while displaying data: ${error}`;
    }
    else if (data.length <= 0) {
        message = "No results found.";
    }

    return (
        <table className={styles.table}>
            <thead>
                <tr className={styles.header}>
                    {columns.map((col) => {
                        return <th key={String(col.key)}>{col.header}</th>
                    })}
                </tr>
            </thead>
            <tbody>
                {message !== '' ? <tr><td colSpan={columns.length || 1}>{message}</td></tr> :
                data.map((row, index) => {
                    return (
                        <tr key={(row as { id: string }).id ?? index}>
                            {columns.map((col) => {
                                const isInvalidValue = row[col.key] === undefined || row[col.key] === null;
                                const displayValue = isInvalidValue ? '' : String(row[col.key]);

                                return (
                                    <td key={String(col.key)}>
                                        {displayValue}
                                    </td>
                                )
                            })}
                        </tr>
                    )
                })}
            </tbody>
        </table>
    )
}