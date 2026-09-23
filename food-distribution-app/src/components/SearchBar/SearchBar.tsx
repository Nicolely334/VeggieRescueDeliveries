import styles from "./styles.module.css";

interface SearchBarProps {
    value: string,
    handleSearch: (s: string) => void
}

export function SearchBar({ value, handleSearch }: SearchBarProps) {
    return (
        <div className={styles.container}>
            <input 
                className={styles.searchInput} 
                type="text" 
                placeholder="Search"
                value={value}
                onChange={(e) => {handleSearch(e.target.value)}}
            />
        </div>
    )
}