'use client';

import { Sidebar } from '@/src/components/ui/Sidebar';
import { usePathname } from 'next/navigation';

import styles from './layout.module.css';

export default function DashboardLayout({ 
    children 
}: { children: React.ReactNode }) {
    const pathName = usePathname().slice(1);
    const header = pathName.charAt(0).toUpperCase() + pathName.slice(1);

    return (
        <div className={styles.container}>
            <Sidebar />
            <main className={styles.main}>
                {children}
            </main>
        </div>
    )
}