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
    if (isLoading) { 
        return (<div>Loading data...</div>);
    }

    if (error) {
        return (<div>Error while displaying data: {error}</div>)
    }

    return (
        <table className={styles.table}>
            <thead>
                <tr>
                    {columns.map((col) => {
                        return <th key={String(col.key)}>{col.header}</th>
                    })}
                </tr>
            </thead>
            <tbody>
                {data.length <= 0 ? <tr><td colSpan={columns.length}>No results found.</td></tr> :
                data.map((row, index) => {
                    return (
                        <tr key={index}>
                            {columns.map((col) => {
                                const rawValue = row[col.key];
                                let displayValue: string;

                                if (rawValue === undefined || rawValue === null)
                                    displayValue = '';
                                else 
                                    displayValue = String(row[col.key]);

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