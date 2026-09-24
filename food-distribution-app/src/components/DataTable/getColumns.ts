import { Column } from "@/src/components/DataTable/DataTable";

/*
    Util function for getting columns from an array of JSON objects.
*/

export function getColumns<T extends object>(data: T[]): Column<T>[] {
    if (data.length <= 0) {
        return [];
    }

    const columns = Object.keys(data[0]) as (keyof T)[];
    const mappedColumns = columns.map((column) => {
        const str = column as string;
        const header = str.charAt(0).toUpperCase() + str.slice(1);

        return { key: column, header: header };
    });

    return mappedColumns;
}