import { Column } from "../DataTable/DataTable";

import styles from "./styles.module.css";

interface SearchBarProps<T> {
    searchValue: string,
    columns: Column<T>[],
    sortByValue: string,
    setSortByValue: (s: string) => void,
    sortAscending: boolean,
    setSortAscending: (b: boolean) => void,
    handleSearch: (s: string) => void
}

export function SearchBar<T>({ 
    searchValue, 
    columns, 
    sortByValue, 
    setSortByValue, 
    sortAscending, 
    setSortAscending, 
    handleSearch 
}: SearchBarProps<T>) {
    return (
        <div className={styles.container}>
            <input 
                className={styles.searchInput} 
                type="text" 
                placeholder="Search"
                value={searchValue}
                onChange={(e) => {handleSearch(e.target.value)}}
            />
        </div>
    )
}